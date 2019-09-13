# IESEG buddy matcher

A simple yet flexible program to match french students with exchange students for the IESEG international club buddy program. It also includes a function to send them a mail informing them that they have been matched.

The matching is done using a hungarian algorithm provided by the PyPI package `munkres`, and the CLI uses `click`+`setuptools`

## Installation

```bash
git clone https://github.com/TimDarcet/IESEG_buddy_matcher.git
cd IESEG_buddy_matcher
pip install -e .
```

## Usage

### Command-line interface

The CLI includes two commands: `match`, to create matchings, and `send_mails`, to send the corresponding e-mails.

`match` takes in a config file and two answers files. It outputs a matchings file and two "remaining" files, containing CSV data about remaining students. The matching is computed using criterias defined in the config file.

`send_mails` takes in the config file and a matchings file. It then sends to all matched buddies a mail informing them of the match. The mail template is configured in the config file.

Their full documentation can be accessed using

```bash
match --help
```

and

```bash
send_mails --help
```

### Configuration

A config file (by default, `./config.json`) is provided to the program. It contains three types of information:

- The labels for special questions
- The criterias for the matching algorithm
- The e-mail templates

#### Syntax

The config uses [JSON](https://jsonformatter.curiousconcept.com/#learn) syntax. For an example, please refer to the [default config file](./config.json) (config file for the 2019 buddy assignements).

#### Special questions

The questions that should be specified in the config file are:

| Label                      | Default | Corresponding question             |
| -------------------------- | ------- | ---------------------------------- |
| two_buddies_question_label | Q7      | Do you accept to take two buddies? |
| fluentQ                    | Q10     | In which languages are you fluent? |
| learningQ                  | Q11     | Which languages are you learning?  |
| firstNameQ                 | Q1      | What is your first name?           |
| lastNameQ                  | Q2      | What is your last name?            |
| eMailQ                     | Q3      | What is your e-mail?               |

#### Criterias

As many criterias as needed can be added to the configuration. All criterias are normalized between 0 and 1, and then scaled using coefficients.

As the syntax for writing one can be complex, it is recommended to look at existing criterias in the default config to understand it.

The attributes for a criterion are:

##### Required attributes

- `coef`: The coeficient (weight) to use for this criterion. Larger means the criterion is more important.
- `type`: The type of criterion. possibilities are:
  - `transform_diff`: Requires `transform` and `QLabel`. Returns the normalized absolute difference between the two answers to the question labeled by the value of `QLabel`, after running the answers through a dictionnary provided by `transform`.
  - `rank`: Requires `QLabel` and `nAnswers`. Returns the normalized Kendall-Tau distance between the two rankings. `nAnswers` has to be the number of items to rank.
  - `has_intersection`: Requires `frQ` and `exQ`. Optional: `singleFr` and `singleEx`, to flag that the input is not a list but a single item. Returns 0 if there is no item in common and 1 if there is one.
  - `inter_over_union`: Requires `QLabel`. Returns the [inter over union](https://www.wikiwand.com/fr/Indice_et_distance_de_Jaccard) of the two sets.
  - `bool`: Requires `QLabel` and `who`. `who` may be either `fr` or `ex`. Returns 1 if the person specified by `who` has `True` in the column `QLabel`.
  - `share_fav_lang`: Requires `fluentQ`, `learningQ`, `favQ` and `favTable`, which respectively specify what are the labels for the question "In which languages are you fluent?", "Which languages are you learning?", and "Would you prefer speaking a fluent or learning language?", and what answers to the "favorite" question correspond to. Returns 1 if the two do not share a language they want to practice.
  - `semi_fav_lang`: Requires `fluentQ`, `learningQ`, `favQ` and `favTable`, which respectively specify what are the labels for the question "In which languages are you fluent?", "Which languages are you learning?", and "Would you prefer speaking a fluent or learning language?", and what answers to the "favorite" question correspond to. Returns 1 if the two do not share a language at least one of them wants to practice.
  - `shared_lang`: Requires `fluentQ` and `learningQ`, which respectively specify what are the labels for the question "In which languages are you fluent?" and "Which languages are you learning?". Returns 1 if the two do not share a language at all.

##### Optional attributes

`condition`: Specifies a condition controlling whether or not this criterion is used. Conditions have to specify a type, and further attributes depend on the type. Possible types are:

- `equals`: Requires `QLabel`, `value` and `who`. Is true only if the answer of the person `who` to the question `QLabel` equals `value`.
- `and`: Requires `condition1` and `condition2`, two conditions. Is true if both sub-conditions are True.

#### E-mail templates

These are under "`mails`". For one template, the label should be the language name, as used in the original form, and the value should be the content of the e-mail. A few special templates can be used so that the mail sent is customized for each person. The templates are to be enclosed in curly brackets `{}`, and their name can be one of the following:

| Name          | Description                        |
| ------------- | ---------------------------------  |
| frFName       | First name of the french student   |
| frLName       | Last name of the french student    |
| frEMail       | E-mail of the french student       |
| exFName       | First name of the exchange student |
| exLName       | Last name of the exchange student  |
| exEMail       | E-mail of the exchange student     |
| language      | A language they have in common     |
| compatibility | A compatibility percentage         |

`\n` characters can be used as line breaks, and the subject line can be used to define a subject.


## Support

For support, contact me at timothee.darcet@gmail.com.

### Known issues

- If a column is empty for all participants, the algorithm will not work. A few empty cells do not break the algorithm but they are not advised as the algorithm will hve to make assumptions about their values

## License

[MIT](./LICENSE)

## Project status

Development has stopped, I am not planning on continuing it.
