import pandas as pd
from munkres import Munkres # Hungarian algorithm
import csv # opening and reading csv files
from sklearn.impute import SimpleImputer
import json


"""
A munkres solver for the IESEG french-international students assignment problem.
The csv files are to be placed in ./data.
"""


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

freqs = {'Once a month' : 1,
         'Twice a month' : 2,
         'Once a week' : 4,
         'Twice a week or more' : 9}

favLangs = {"A language you are learning": 1,
            "A language you are fluent in": 0}

coefs = {'Q8':2,
         'Q9':1,
         'shareFavLang':5,
         'sharedLang':1000,
         'semiFavLang':5,       
         'formerUni':3,
         'futureUni':3,
         'interestedInCulture':3,
         'Q20':4,
         'Q21':1,
         'Q22':1,
         'Q23':1,
         'Q24':1,
         'clone': 500
        }

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
    return int(len(frLangs[fav['fr']].intersection(exLangs[fav['ex']])) == 0)  # Do they have no preferred language in common ?

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
    return int(len(frLangs[1 - fav['fr']].intersection(exLangs[fav['ex']]).union(frLangs[1 - fav['fr']].intersection(exLangs[1 - fav['ex']]))) == 0)

def sharedLangCost(criterion, frRow, exRow):
    """Returns 1 if the two do not share a language, else 0"""
    fluentQ = criterion['fluentQ']
    learningQ = criterion['learningQ']
    frLangs = [set(frRow[fluentQ].split(',')),
                set(frRow[learningQ].split(','))]
    exLangs = [set(exRow[fluentQ].split(',')),
                set(exRow[learningQ].split(','))]
    # Do they share no language ?
    return int(len(frLangs[0].union(frLangs[1]).intersection(exLangs[0].union(exLangs[1]))) == 0)

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
    c2 = cond["condition2"]
    c1 = cond["condition1"]
    return resolveCond(c1, frRow, exRow) and resolveCond(c2, frRow, exRow)

def equalsCond(cond, frRow, exRow):
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
    return condFuncs[cond["type"]](cond, frRow, exRow)

def totalCost(criterias, frRow, exRow):
    cost = 0
    for criterion in criterias.values():
        if "condition" not in criterion or resolveCond(criterion["condition"], frRow, exRow):
            cost += costFuncs[criterion["type"]](criterion, frRow, exRow)
    return cost


with open('config.json', 'r') as conf_file:
    criterias = json.load(conf_file)

# import data
fr = pd.read_csv("./data/french.csv")
ex = pd.read_csv("./data/exchange.csv")

# Drop irrelevant columns
columnsToDrop = list(filter(lambda x: x[0] != 'Q', fr.columns)) + ['Q{}'.format(i) for i in range(3, 7)]
frAnswers = fr.drop(columns=columnsToDrop)
exAnswers = ex.drop(columns=columnsToDrop)

# Drop title indexes
frAnswers = frAnswers.drop(index=[0, 1])
exAnswers = exAnswers.drop(index=[0, 1])

# Impute missing values
imp = SimpleImputer(strategy="most_frequent")
frAnswers = pd.DataFrame(imp.fit_transform(frAnswers), columns=frAnswers.columns)
exAnswers = pd.DataFrame(imp.fit_transform(exAnswers), columns=exAnswers.columns)


# Clone the frenchies who accept to take two exchange partners
frAnswers.Q7 = frAnswers.Q7.map(repeat.get)
frAnswers['clone'] = False
fraClones = frAnswers.copy(deep=True)[frAnswers['Q7']]
fraClones['clone'] = True
frAnswers = pd.concat([frAnswers, fraClones])
frAnswers = frAnswers.reset_index(drop=True)


# Compute the costs 
costMatrix = [[float('inf')] * len(exAnswers.index) for _ in range(len(frAnswers.index))] 
 

for fridx, fr_row in frAnswers.iterrows():
    for exidx, ex_row in exAnswers.iterrows():
        # Compute a list of compatibility scores
        # Scores are normalized between 0 and 1
        costMatrix[fridx][exidx] = totalCost(criterias, fr_row, ex_row)
        # scores = dict()
        # scores['Q8'] = abs(freqs[fr_row['Q8']] - freqs[ex_row['Q8']]) / 9
        # scores['Q9'] = n_inv(list(fr_row['Q9_{}'.format(i)] for i in range(1, 3)),
        #                      list(ex_row['Q9_{}'.format(i)] for i in range(1, 3))) / 3
        # frLangs = [set(fr_row['Q10'].split(',')),
        #            set(fr_row['Q11'].split(','))]
        # exLangs = [set(ex_row['Q10'].split(',')),
        #            set(ex_row['Q11'].split(','))]
        # fav = {'fr': favLangs[fr_row['Q12']],
        #        'ex': favLangs[ex_row['Q12']]}
        # scores['shareFavLang'] = int(len(frLangs[fav['fr']].intersection(exLangs[fav['ex']])) == 0)  # Do they have no preferred language in common ?
        # # Do they have no language that both of them speak, but one would prefer not to speak ?        
        # scores['semiFavLang'] = int(len(frLangs[1 - fav['fr']].intersection(exLangs[fav['ex']]).union(frLangs[1 - fav['fr']].intersection(exLangs[1 - fav['ex']]))) == 0)
        # # Do they share no language ?
        # scores['sharedLang'] = int(len(frLangs[0].union(frLangs[1]).intersection(exLangs[0].union(exLangs[1]))) == 0)
        # # Has the french ever been in exchange in the exchange student's university ?
        # scores['formerUni'] = 1 - int(fr_row['Q13'] == "Yes" == fr_row['Q15'] and fr_row['Q14'] == ex_row['Q26'])
        # # Will the french go to the exchange student's university ?
        # scores['futureUni'] = 1 - int(fr_row['Q16'] == "Yes" == fr_row['Q18'] and fr_row['Q17'] == ex_row['Q26'])
        # # TODO: Set or remove condition if relevant
        # scores['interestedInCulture'] = 1 - int(ex_row['Q19'] in fr_row['Q19'].split(','))
        # scores['Q20'] = n_inv(list(fr_row['Q20_{}'.format(i)] for i in range(1, 4)),
        #                       list(ex_row['Q20_{}'.format(i)] for i in range(1, 4))) / 6
        # frSports = set(fr_row['Q21'].split(','))
        # exSports = set(ex_row['Q21'].split(','))
        # # Proportion of sports they have in common
        # scores['Q21'] = 1 - len(frSports.intersection(exSports)) / len(frSports.union(exSports))
        # scores['Q22'] = int(fr_row['Q22'] != ex_row['Q22'])
        # scores['Q23'] = int(fr_row['Q23'] != ex_row['Q23'])
        # scores['Q24'] = int(fr_row['Q24'] != ex_row['Q24'])
        # scores['clone'] = int(fr_row['clone'])
        # costMatrix[fridx][exidx] = sum(coefs[key] * scores[key] for key in scores)


# Solve the assignment problem using munkres
m = Munkres()
assignments = m.compute(costMatrix)

# Print results
for fridx, exidx in assignments:
    print(frAnswers['Q1'][fridx], frAnswers['Q2'][fridx],
          '<3',
          exAnswers['Q1'][exidx], exAnswers['Q2'][exidx],
          costMatrix[fridx][exidx])
