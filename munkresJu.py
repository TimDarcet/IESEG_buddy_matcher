import pandas as pd
from munkres import Munkres # Hungarian algorithm
import csv # opening and reading csv files
from sklearn.impute import SimpleImputer
import json
import click


"""
A munkres solver for the IESEG french-international students assignment problem.
The csv files are to be placed in ./data.
"""

def compatPercentage(n):
    if n >= 500:
        n -= 500  # Remove the cost caused by cloning
    return '{:2.2f}%'.format(100 * max(0, 1 - n / 25))

def n_inv(r1, r2):
    """ Calculates the Kendall-tau distance between two rankings,
    i.e. the number of inversions between the two sequences.
    r1 and r2 are iterables so that r1[i] is the ranking of the i-th element."""
    assert len(r1) == len(r2)
    n = 0
    for i in range(len(r1)):
        for j in range(i):
            n += bool((r1[i] < r1[j]) ^ (r2[i] < r2[j]))
    return n

repeat = {"Yes": True, "No": False}

def transformDiffCost(criterion, frRow, exRow):
    """Returns the absolute difference between their image through the 'transform' dict, normalized"""
    t = criterion['transform']
    q = criterion['QLabel']
    return abs(t[frRow[q]] -
               t[exRow[q]]) / max(t.values())

def rankCost(criterion, frRow, exRow):
    """Returns the number of inversions between the two rankingsm normalized"""
    n = criterion['nAnswers']
    q = criterion['QLabel']
    return n_inv(list(frRow[q + '_{}'.format(i)] for i in range(1, n + 1)),
                 list(exRow[q + '_{}'.format(i)] for i in range(1, n + 1))) / (n * (n - 1) / 2) 

def shareFavLangCost(criterion, frRow, exRow):
    """Returns 0 if the two share a favorite language, else 1"""
    fluentQ = criterion['fluentQ']
    learningQ = criterion['learningQ']
    favT = criterion['favTable']
    favQ = criterion['favQ']
    frLangs = [set(frRow[fluentQ].split(',')),
                set(frRow[learningQ].split(','))]
    exLangs = [set(exRow[fluentQ].split(',')),
                set(exRow[learningQ].split(','))]
    fav = {'fr': favT[frRow[favQ]],
           'ex': favT[exRow[favQ]]}
    # Do they have no preferred language in common ?
    return int(len(frLangs[fav['fr']].intersection(exLangs[fav['ex']])) == 0)

def semiFavLangCost(criterion, frRow, exRow):
    """Returns 0 if the two share a language that is a favorite for one of the two, else 1"""
    fluentQ = criterion['fluentQ']
    learningQ = criterion['learningQ']
    favT = criterion['favTable']
    favQ = criterion['favQ']
    frLangs = [set(frRow[fluentQ].split(',')),
                set(frRow[learningQ].split(','))]
    exLangs = [set(exRow[fluentQ].split(',')),
                set(exRow[learningQ].split(','))]
    fav = {'fr': favT[frRow[favQ]],
           'ex': favT[exRow[favQ]]}
    # Do they have no language that both of them speak, but one would prefer not to speak ?        
    return int(len(frLangs[1 - fav['fr']].intersection(exLangs[fav['ex']])\
            .union(frLangs[fav['fr']].intersection(exLangs[1 - fav['ex']]))) == 0)

def sharedLangCost(criterion, frRow, exRow):
    """Returns 1 if the two do not share a language, else 0"""
    fluentQ = criterion['fluentQ']
    learningQ = criterion['learningQ']
    frLangs = [set(frRow[fluentQ].split(',')),
                set(frRow[learningQ].split(','))]
    exLangs = [set(exRow[fluentQ].split(',')),
                set(exRow[learningQ].split(','))]
    # Do they share no language ?
    return int(len(frLangs[0].union(frLangs[1])\
     .intersection(exLangs[0].union(exLangs[1]))) == 0)

def hasIntersectionCost(criterion, frRow, exRow):
    """Returns 1 if the two do not share an answer on the specified question, else 0"""
    frQ = criterion['frQ']
    exQ = criterion['exQ']
    if 'singleFr' in criterion and criterion['singleFr']:
        frSet = set([frRow[frQ]])
    else:
        frSet = set(frRow[frQ].split(','))
    if 'singleEx' in criterion and criterion['singleEx']:
        exSet = set([exRow[exQ]])
    else:
        exSet = set(exRow[exQ].split(','))
    return int(len(frSet.intersection(exSet)) == 0)

def interOverUnionCost(criterion, frRow, exRow):
    """Returns one minus the number of answers they have in common divided by the number they have combined"""
    q = criterion['QLabel']
    frSet = set(frRow[q].split(','))
    exSet = set(exRow[q].split(','))
    # Proportion of sports they have in common
    return 1 - len(frSet.intersection(exSet)) / len(frSet.union(exSet))

def boolCost(criterion, frRow, exRow):
    """Returns 1 if the label is set to Truem else 0
    'who' allows to choose the nationality affected"""
    q = criterion['QLabel']
    w = criterion['who']
    if w == 'fr':
        row = frRow
    elif w == 'ex':
        row = exRow
    else:
        raise ValueError("'who' was not specified in criterion ", criterion)
    return int(row[q])

costFuncs = {
    "transform_diff": transformDiffCost,
    "rank": rankCost,
    "share_fav_lang": shareFavLangCost,
    "semi_fav_lang": semiFavLangCost,
    "shared_lang": sharedLangCost,
    "has_intersection": hasIntersectionCost,
    "inter_over_union": interOverUnionCost,
    "bool": boolCost
}

def andCond(cond, frRow, exRow):
    """Parses an and condition and checks whether it is true on these rows"""
    c2 = cond["condition2"]
    c1 = cond["condition1"]
    return resolveCond(c1, frRow, exRow) and resolveCond(c2, frRow, exRow)

def equalsCond(cond, frRow, exRow):
    """Parses an equals condition and checks whether it is true on these rows"""
    q = cond["QLabel"]
    v = cond["value"]
    w = cond["who"]
    if w == 'fr':
        row = frRow
    elif w == 'ex':
        row = exRow
    else:
        raise ValueError("'who' was not specified in condition ", cond)
    return row[q] == v

condFuncs = {
    "and": andCond,
    "equals": equalsCond
}

def resolveCond(cond, frRow, exRow):
    """Parses a condition and checks whether it is true on these rows"""
    return condFuncs[cond["type"]](cond, frRow, exRow)

def totalCost(criterias, frRow, exRow):
    cost = 0
    for criterion in criterias.values():
        if "condition" not in criterion or resolveCond(criterion["condition"], frRow, exRow):
            cost += costFuncs[criterion["type"]](criterion, frRow, exRow)
    return cost

def prepare(answers, doClone=False, cloneLabel=None):
    """Prepare the answers dataframe"""
    # Drop title indexes
    answers = answers.drop(index=[0, 1])
    answers = answers.reset_index(drop=True)
    # Ad-hoc solution so that the imputer does not drop the empty columns
    problemColumns = ["RecipientLastName",
        "RecipientFirstName",
        "RecipientEmail",
        "ExternalReference"]
    for col in problemColumns:
        answers[col][0] = 0
    # Impute missing values
    imp = SimpleImputer(strategy="most_frequent")
    tmp = imp.fit_transform(answers)
    answers = pd.DataFrame(tmp, columns=answers.columns)
    # Clone the frenchies who accept to take two exchange partners
    if doClone:
        clones = answers.copy(deep=True)[answers[cloneLabel].map(repeat.get)]
        answers['clone'] = False
        clones['clone'] = True
        answers[cloneLabel] = False
        clones[cloneLabel] = False
        answers = pd.concat([answers, clones])
        answers = answers.reset_index(drop=True)

    return answers


@click.command()
@click.option("--conf-file", '-c',
              default="config.json",
              type=click.File(),
              help="The JSON configuration file")
@click.option("--french-ans", '-f',
              default="./data/french.csv",
              type=click.Path(exists=True, dir_okay=False),
              help="The french answers CSV file")
@click.option("--exchange-ans", '-e',
              default="./data/exchange.csv",
              type=click.Path(exists=True, dir_okay=False),
              help="The exchange student answers CSV file")
@click.option("--remaining-fr", '-rf',
              default="./output/remainingFr.csv",
              type=click.File(mode="w"),
              help="The file into which the remaining unmatched french should be outputted")
@click.option("--remaining-ex", '-re',
              default="./output/remainingEx.csv",
              type=click.File(mode="w"),
              help="The file into which the remaining unmatched exchange students should be outputted")
@click.option("--matchings-file", '-m',
              default="./output/matchings.csv",
              type=click.File(mode="w"),
              help="The file into which the remaining unmatched french should be outputted")
@click.option("--verbose", '-v',
              count=True,
              help="Show more info in stderror")
def match(conf_file, french_ans, exchange_ans, remaining_fr, remaining_ex, matchings_file, verbose):
    config = json.load(conf_file)
    criterias = config['criterias']

    # import data
    fr = pd.read_csv(french_ans)
    ex = pd.read_csv(exchange_ans)

    frAnswers = prepare(fr, doClone=True, cloneLabel=config['two_buddies_question_label'])
    exAnswers = prepare(ex)

    # Compute the costs 
    costMatrix = [[float('inf')] * len(exAnswers.index) for _ in range(len(frAnswers.index))]
    for fridx, fr_row in frAnswers.iterrows():
        for exidx, ex_row in exAnswers.iterrows():
            # Compute a list of compatibility scores
            # Scores are normalized between 0 and 1
            costMatrix[fridx][exidx] = totalCost(criterias, fr_row, ex_row)

    # Solve the assignment problem using munkres
    m = Munkres()
    assignments = m.compute(costMatrix)

    # Print results
    if verbose > 0:
        for fridx, exidx in assignments:
            print(frAnswers['Q1'][fridx], frAnswers['Q2'][fridx],
                '<3',
                exAnswers['Q1'][exidx], exAnswers['Q2'][exidx],
                compatPercentage(costMatrix[fridx][exidx]))


    # Output remaining unmatched people
    frMatched, exMatched = zip(*assignments)
    frAnswers[~frAnswers.index.isin(frMatched)].to_csv(remaining_fr)
    exAnswers[~exAnswers.index.isin(exMatched)].to_csv(remaining_ex)

    # Outputing matchings
    matchings = pd.DataFrame(columns=["frFName",
                                      "frLName",
                                      "frEMail",
                                      "exFName",
                                      "exLName",
                                      "exEMail",
                                      "language"])
    for fridx, exidx in assignments:
        fQ, lQ = config["fluentQ"], config["learningQ"]
        fnQ, lnQ, emQ = config["firstNameQ"], config["lastNameQ"], config["eMailQ"]
        frRow = frAnswers.iloc[fridx]
        exRow = exAnswers.iloc[exidx]
        commonLangs = set(frRow[fQ].split(',')).intersection(set(exRow[fQ].split(',')))
        for lang in config["mails"]:
            if lang in commonLangs:
                chosenLang = lang
        else:
            chosenLang = "English"
        d = {"frFName": frRow[fnQ],
            "frLName": frRow[lnQ],
            "frEMail": frRow[emQ],
            "exFName": exRow[fnQ],
            "exLName": exRow[lnQ],
            "exEMail": exRow[emQ],
            "language": chosenLang}
        matchings = matchings.append(d, ignore_index=True)

    matchings.to_csv("./output/matchings.csv")
