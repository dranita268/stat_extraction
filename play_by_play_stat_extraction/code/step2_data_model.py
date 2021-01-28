import json
from datetime import datetime
now = str(datetime.now())
import os

try:
    os.mkdir('Data Models')
except FileExistsError:
    pass


'''
For each ParentName, what roles are expected.
'''
ParentName_role_model = {
    # --- NONPLAY
    'GameType': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'TeamName': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'GameDate': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'Location': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'Attendance': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'Weather': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'GameKickoffTime': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'Toss': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'Poss': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'PageNo': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'Score': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'GameClock': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'Period': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'OtherText': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},

    # --- SCRIM
    'PuntReturn': {'moff': ['punter'],
                   'asoff': [],
                   'deff': ['returner'],
                   'cont': []},
    'PuntTB': {'moff': ['punter'],
               'asoff': [],
               'deff': [],
               'cont': []},
    'PuntOOB': {'moff': ['punter'],
                'asoff': [],
                'deff': [],
                'cont': []},
    'PuntFC': {'moff': ['punter'],
               'asoff': [],
               'deff': ['returner'],
               'cont': []},
    'PuntDowned': {'moff': ['punter'],
                   'asoff': [],
                   'deff': ['returner'],
                   'cont': []},
    'PuntFake': {'moff': ['punter'],
                   'asoff': [],
                   'deff': [],
                   'cont': []},
    'PuntBlocked': {'moff': ['punter'],
                    'asoff': [],
                    'deff': ['blocker'],
                    'cont': []},
    'PuntDead': {'moff': ['punter'],
                 'asoff': [],
                 'deff': [],
                 'cont': []},
    'RushSimple': {'moff': ['rusher'],
                   'asoff': [],
                   'deff': ['tackler'],
                   'cont': []},
    'RushFumble': {'moff': ['rusher+fumbler'],
                   'asoff': [],
                   'deff': ['tackler'],
                   'cont': []},
    'RushTD': {'moff': ['rusher+scorer'],
               'asoff': [],
               'deff': [],
               'cont': []},
    'RushFD': {'moff': ['rusher'],
               'asoff': [],
               'deff': ['tackler'],
               'cont': []},
    'RushSAF': {'moff': ['rusher+scorer'],
                'asoff': [],
                'deff': [],
                'cont': []},
    'RushTimeout': {'moff': ['rusher'],
                    'asoff': [],
                    'deff': [],
                    'cont': []},
    'PassComplete': {'moff': ['passer'],
                     'asoff': ['receiver'],
                     'deff': ['tackler'],
                     'cont': []},
    'PassIncomplete': {'moff': ['passer'],
                       'asoff': ['receiver'],
                       'deff': ['tackler'],
                       'cont': []},
    'PassBrokenUp': {'moff': ['passer'],
                     'asoff': ['receiver'],
                     'deff': ['breaker'],
                     'cont': []},
    'PassDrop': {'moff': ['passer'],
                 'asoff': ['receiver'],
                 'deff': [],
                 'cont': []},
    'PassSack': {'moff': ['passer'],
                 'asoff': [],  # removed the receiver role
                 'deff': ['sacker'],
                 'cont': []},
    'PassInterception': {'moff': ['passer'],
                         'asoff': ['receiver'],
                         'deff': ['intercepter'],
                         'cont': []},
    'PassTD': {'moff': ['passer+scorer'],
               'asoff': ['receiver'],
               'deff': [],
               'cont': []},
    'PassFD': {'moff': ['passer'],
               'asoff': ['receiver'],
               'deff': [],
               'cont': []},
    'PassSAF': {'moff': ['passer+scorer'],
                'asoff': ['receiver'],
                'deff': ['saf'],
                'cont': []},
    'PassTimeout': {'moff': ['passer'],
                    'asoff': ['receiver'],
                    'deff': [],
                    'cont': []},
    'PresnapPenalty': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},

    'FGGood': {'moff': ['fgattempter+scorer'],
               'asoff': [],
               'deff': [],
               'cont': []},
    'FGBad': {'moff': ['fgattempter'],
              'asoff': [],
              'deff': [],
              'cont': []},
    'FGFake': {'moff': ['fgattempter'],
               'asoff': [],
               'deff': [],
               'cont': []},
    'FGBlock': {'moff': ['fgattempter'],
                'asoff': [],
                'deff': ['blocker'],
                'cont': []},

    # --- NONSCRIM
    'KickoffReturn': {'moff': ['kicker'],
                      'asoff': [],
                      'deff': ['returner'],
                      'cont': []},
    'KickoffTB': {'moff': ['kicker'],
                  'asoff': [],
                  'deff': ['returner'],
                  'cont': []},
    'KickoffOOB': {'moff': ['kicker'],
                   'asoff': [],
                   'deff': [],
                   'cont': []},
    'KickoffFC': {'moff': ['kicker'],
                  'asoff': [],
                  'deff': [],
                  'cont': []},
    'KickoffOnSideAttempt': {'moff': ['kicker'],
                             'asoff': [],
                             'deff': [],
                             'cont': []},
    'PATKickGood': {'moff': ['patkicker+scorer'],
                    'asoff': [], 
                    'deff': [], 
                    'cont': []},
    'PATKickBad': {'moff': ['patkicker'],
                   'asoff': [], 
                   'deff': [], 
                   'cont': []},
    'PATKickBlock': {'moff': ['patkicker'],
                     'asoff': [],
                     'deff': ['blocker'],
                     'cont': []},
    'PAT2RushGood': {'moff': ['patrusher+scorer'],
                     'asoff': [],
                     'deff': [],
                     'cont': []},
    'PAT2RushBad': {'moff': ['patrusher'],
                    'asoff': [],
                    'deff': ['tackler'],
                    'cont': []},
    'PAT2RushFumble': {'moff': ['patrusher+fumbler'],  # was there a scoring in this case?
                       'asoff': [],
                       'deff': [],
                       'cont': []},
    'PAT2PassComplete': {'moff': ['patpasser+scorer'],
                         'asoff': ['receiver'],
                         'deff': [],
                         'cont': []},
    'PAT2PassIncomplete': {'moff': ['patpasser'],
                           'asoff': ['receiver'],
                           'deff': [],
                           'cont': []},
    'PAT2PassBrokenUp': {'moff': ['patpasser'],
                         'asoff': ['receiver'],
                         'deff': ['breaker'],
                         'cont': []},
    'PAT2PassDrop': {'moff': ['patpasser'],
                     'asoff': ['receiver'],
                     'deff': [],
                     'cont': []},
    'PAT2PassSack': {'moff': ['patpasser'],
                     'asoff': ['receiver'],
                     'deff': ['sacker'],
                     'cont': []},
    'PAT2PassInterception': {'moff': ['patpasser'],
                             'asoff': ['receiver'],
                             'deff': ['intercepter'],
                             'cont': []},

    # --- OTHERS. More like team stats
    'Penalty': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'TimeOut': {'moff': [], 'asoff': [], 'deff': [], 'cont': []},
    'Dead': {'moff': [], 'asoff': [], 'deff': [], 'cont': []}
}


with open('Data Models/ParentName_role_model.json', 'w') as file:
    json.dump(ParentName_role_model, file)

print('loop 2 ParentName and roles relationship is updated on {}\n'.format(now))


# -------------------------------------------------------------------------------------
'''
For each role, what stats are expected. 
'''
role_stats_model = {
    'fumbler': {'stat key': 'fumble',
                # stat key is the key in empty player agg stats template
                # so that rush yards can be tell part from pass yards etc
                'role_based': ['fumble'],
                'temp_based': ['fumbleforced', 'fumblelost', 'fumblercov_team', 'fumblercov_opp']},
    'scorer': {'stat key': 'score',
               'role_based': ['score'],
               'temp_based': ['pts']},  # score bool, how many points 'fg', 'saf', 'td', 'pat']},
    'rusher': {'stat key': 'rush',
               'role_based': ['rush'],
               'temp_based': ['yds', 'fd', 'td', 'gain', 'loss', 'fumble', 'pts']},
    'tackler': {'stat key': 'tackle',
                'role_based': ['tackle', 'tackua', 'tacka'],
                'temp_based': []},
    'punter': {'stat key': 'punt',
               'role_based': ['punt'],
               'temp_based': ['yds', 'fc', 'inside20', 'inside10', 'blkd', 'plus50', 'tb', 'fake', 'ob', 'dead']},
    'returner': {'stat key': 'return',
                 'role_based': ['return'],
                 'temp_based': ['yds', 'td']},
    'passer': {'stat key': 'pass',
               'role_based': ['pass'],
               'temp_based': ['yds', 'complete', 'incomplete', 'brup', 'td', 'fd', 'int', 'sack', 'pts']},
    'receiver': {'stat key': 'receive',
                 'role_based': ['receive'],
                 'temp_based': ['yds', 'complete', 'incomplete']},
    'sacker': {'stat key': 'sack',
               'role_based': ['sack'],
               'temp_based': ['yds']},
    'breaker': {'stat key': 'brup',
                'role_based': ['brup'],
                'temp_based': []},
    'blocker': {'stat key': 'defense',
                'role_based': ['blkd'],
                'temp_based': []},
    'intercepter': {'stat key': 'int',
                    'role_based': ['int'],
                    'temp_based': ['yds']},
    'kicker': {'stat key': 'ko',
               'role_based': ['ko'],  # the player who kicked off the ball
               'temp_based': ['yds', 'tb', 'ona', 'ob', 'fc']},
    'fgattempter': {'stat key': 'fga',
                    'role_based': ['fga'],
                    'temp_based': ['good', 'bad', 'blkd','fake','pts']},  # not sure whether to put fake here
    # 'holder': {'stat key': 'hold',
    #            'role_based': ['hold'],
    #            'temp_based': []},
    'patkicker': {'stat key': 'patkick',
                  'role_based': ['patkick'],
                  'temp_based': ['good', 'bad','pts']},
    'patrusher': {'stat key': '',
                  'role_based': ['patrush'],
                  'temp_based': ['good', 'bad', 'fumble','pts']},
    'patpasser': {'stat key': '',
                  'role_based': ['patpass'],
                  'temp_based': ['good', 'bad', 'brup','pts']}
}
#  For pass, receive, pat, fg, they are all attempts. No matter whether the attempt was successful or not.
#  E.G. A Failed receiving will have
# receiver: receive = 1, complete = 0, incomplete = 1. The final receiving stats is the product of attempt and the bool
with open('Data Models/loop_2_role_stats_model.json', 'w') as file:
    json.dump(role_stats_model, file)

print('loop 2 role stats model is updated on {}\n'.format(now))


# -------------------------------------------------------------------------------------
'''
For each template-based stat, what are its template to search for. 
'''

stat_templates_model = {
    'yds': [r'[0-9]{1,2} (?:yards*|yds*)',
            r'(?:gain[sed]{0,2}|lost|loss) [0-9]{1,2}',
            r'(?:for|of) [0-9]{1,2}'],
    'gain': [r'gain[sed]{0,2}'],
    'loss': [r'loss', r'lost'],
    'fake': [],
    'tb': [],
    'fg': [],
    'ob': [],  # out of bounds

    'td': [],
    'pat': [],
    'blkd': [],
    'fumble': [],
    'complete': [],
    'incomplete': [],
    'good': [],
    'bad': [],
    'ona': [],
    'brup': [],

    'int': [],
    'sack': [],

    'fc': [],
    'fd': [],
    'saf': [],

    'fumbleforced': [r'force[sd]{0,2}'],
    'fumblelost': [r'fumbl[sed]{0,2}.+lost'],
    'fumblercov_team': [r'[a-z]'],  # fumble recovered by the same team, poss WON'T change in the next play
    'fumblercov_opp': [r'[a-z]'],   # fumble recovered by the oppo team, poss WILL  change in the next play

    'inside20': [],  # coded separately
    'inside10': [],  # coded separately
    'plus50': [],  # coded separately
    'pts': [],  # coded separately
}

with open('Data Models/sentence_pattern_model.json', 'r') as j:
    sentence_pattern_model = json.loads(j.read())

stat_templates_model['fake'] = sentence_pattern_model.get('results').get('Fake')
stat_templates_model['fumble'] = sentence_pattern_model.get('results').get('Fumble')
stat_templates_model['tb'] = sentence_pattern_model.get('results').get('Touchback')
stat_templates_model['fg'] = sentence_pattern_model.get('actions').get('SCRIM').get('FieldGoal')
stat_templates_model['ob'] = sentence_pattern_model.get('results').get('Out_of_bounds')
stat_templates_model['td'] = sentence_pattern_model.get('results').get('Touchdown')
stat_templates_model['pat'] = sentence_pattern_model.get('actions').get('NONSCRIM').get('Pat')
stat_templates_model['blkd'] = sentence_pattern_model.get('results').get('Blocked')
stat_templates_model['complete'] = sentence_pattern_model.get('results').get('Complete')
stat_templates_model['incomplete'] = sentence_pattern_model.get('results').get('Incomplete')
stat_templates_model['good'] = sentence_pattern_model.get('results').get('Complete')
stat_templates_model['bad'] = sentence_pattern_model.get('results').get('Incomplete')
stat_templates_model['ona'] = sentence_pattern_model.get('results').get('On_side_kick')
stat_templates_model['brup'] = sentence_pattern_model.get('results').get('Break_up')
stat_templates_model['fc'] = sentence_pattern_model.get('results').get('Fair_catch')
stat_templates_model['fd'] = sentence_pattern_model.get('results').get('First_down')
stat_templates_model['saf'] = sentence_pattern_model.get('results').get('Safety')
stat_templates_model['dead'] = sentence_pattern_model.get('results').get('Dead')
stat_templates_model['int'] = sentence_pattern_model.get('results').get('Interception')
stat_templates_model['sack'] = sentence_pattern_model.get('results').get('Sack')

with open('Data Models/loop_2_stat_templates_model.json', 'w') as file:
    json.dump(stat_templates_model, file)

print('loop 2 stat templates are updated on {}\n'.format(now))


# -------------------------------------------------------------------------------------
'''
For Validation: The rules for ending context computing
'''
ParentName_context_model = {
    # --- SCRIM
    'PuntReturn': {
        'poss_change': True,
        'e_down': '1',
        'e_ytg': 10,
        'e_spot': 'xx'},
    'PuntTB': {
        'poss_change': True,
        'e_down': '1',
        'e_ytg': 10,
        'e_spot': 20},
    'PuntOOB': {
        'poss_change': True,
        'e_down': '1',
        'e_ytg': 10,
        'e_spot': 'xx'},
    'PuntFC': {
        'poss_change': True,
        'e_down': '1',
        'e_ytg':10,
        'e_spot':'xx'},
    'PuntDowned': {
        'poss_change': True,
        'e_down': '1',
        'e_ytg': 10,
        'e_spot': 'xx'},
    'PuntFake': {  # will be skipped for general cases
        'poss_change': False,
        'e_down': '1',
        'e_ytp': 10,
        'e_spot': 'xx'},
    'PuntBlocked': {  # will be skipped for general cases
        'poss_change': True,
        'e_down': '1',
        'e_ytg': 10,
        'e_spot': 'xx'},

    'RushSimple': {
        'poss_change': False,
        'e_down': 'plus 1',
        'e_ytg': 'xx',
        'e_spot': 'xx'},
    'RushFumble': {  # will be skipped for general cases
        'poss_change': False,
        'e_down': 'plus 1',
        'e_ytg': 'xx',
        'e_spot': 'xx'},
    'RushTD': {
        'poss_change': False,  # score validation only
        'e_down': '1',
        'e_ytg': 10,
        'e_spot': 'xx'},
    'RushFD': {
        'poss_change': False,
        'e_down': '1',
        'e_ytg': 10,
        'e_spot': 'xx'},
    'RushSAF': {
        'poss_change': True,  # score validation only
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},
    'RushTimeout': {
        'poss_change': False,
        'e_down': 'no change',
        'e_ytg': 'xx',
        'e_spot': 'xx'},

    'PassComplete': {
        'poss_change': False,
        'e_down': 'plus 1',
        'e_ytg': 'xx',
        'e_spot': 'xx'},
    'PassIncomplete': {
        'poss_change': False,
        'e_down': 'plus 1',
        'e_ytg': 'xx',
        'e_spot': 'xx'},
    'PassBrokenUp': {
        'poss_change': False,
        'e_down': 'plus 1',
        'e_ytg': 'xx',
        'e_spot': 'xx'},
    'PassDrop': {
        'poss_change': False,
        'e_down': 'plus 1',
        'e_ytg': 'xx',
        'e_spot': 'xx'},
    'PassSack': {
        'poss_change': False,
        'e_down': 'plus 1',
        'e_ytg': 'xx',
        'e_spot': 'xx'},
    'PassInterception': {
        'poss_change': True,
        'e_down': '1',
        'e_ytg': 10,
        'e_spot': 'xx'},
    'PassTD': {
        'poss_change': False,  # Score validation only
        'e_down': '1',
        'e_ytg': 10,
        'e_spot': 'xx'},
    'PassFD': {
        'poss_change': False,
        'e_down': '1',
        'e_ytg': 10,
        'e_spot': 'xx'},
    'PassSAF': {
        'poss_change': True,  # Score validation only
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},
    'PassTimeout': {
        'poss_change': False,
        'e_down': 'no change',
        'e_ytg': 'xx',
        'e_spot': 'xx'},

    'PresnapPenalty': {  # skipped for now
        'poss_change': False,
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},

    'FGGood': {  # skipped
        'poss_change': False,
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},
    'FGBad': {  # skipped
        'poss_change': False,
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},
    'FGFake': {  # skipped
        'poss_change': False,
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},
    'FGBlock': {  # skipped
        'poss_change': False,
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},

    # --- NONSCRIM
    'KickoffReturn': {
        'poss_change': True,
        'e_down': '1',
        'e_ytg': 10,
        'e_spot': 'xx'},
    'KickoffTB': {
        'poss_change': True,
        'e_down': '1',
        'e_ytg': 10,
        'e_spot': 25},
    'KickoffOOB': {  # penalty and re-kick
        'poss_change': True,
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},
    'KickoffFC': {
        'poss_change': True,
        'e_down': '1',
        'e_ytg': 10,
        'e_spot': 'xx'},
    'KickoffOnSideAttempt': {
        'poss_change': False,  # sometime changes
        'e_down': 1,
        'e_ytg': 10,
        'e_spot': 'xx'},

    'PATKickGood': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation
    'PATKickBad': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation
    'PATKickBlock': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation
    'PAT2RushGood': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation
    'PAT2RushBad': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation
    'PAT2RushFumble': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation
    'PAT2PassComplete': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation
    'PAT2PassIncomplete': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation
    'PAT2PassBrokenUp': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation
    'PAT2PassDrop': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation
    'PAT2PassSack': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation
    'PAT2PassInterception': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation

    # --- OTHERS. More like team stats
    'Penalty': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation
    'TimeOut': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation
    'Dead': {  # No Validation.
        'poss_change': 'xx',
        'e_down': 'xx',
        'e_ytg': 'xx',
        'e_spot': 'xx'},  # no validation
}

with open('Data Models/ParentName_context_validation_model.json', 'w') as file:
    json.dump(ParentName_context_model, file)

print('The ParentName_context_validation_model is updated on {}\n'.format(now))


# -------------------------------------------------------------------------------------
'''
For player stats aggregation
'''

empty_player_agg_stats = {
    'rush': {'att': 0,
             'yds': 0,
             'gain': 0,
             'loss': 0,
             'td': 0,
             'fd': 0
             # 'long': 0
    },

    'pass': {'att': 0,
             'complete': 0,
             'incomplete': 0,
             'int': 0,
             'yds': 0,
             'td': 0,
             'fd': 0,
             # 'long': 0,
             'sack': 0,
             'sackyds': 0
    },
    'receive': {'no': 0,
                'complete': 0,
                'incomplete': 0,
                'yds': 0
                # 'td': 0,
                # 'long': 0
    },
    'int': {'no': 0,
            'yds': 0
    },
    'sack': {'no': 0,
             'yds': 0},
    'brup': {'no': 0},
    'defense': {
        'tacka': 0,
        'tackua': 0,
        'tflua': 0,
        'tfla': 0,
        'tflyds': 0,
        'ff': 0,
        'fr': 0,
        'fryds': 0},
    'fumble': {'no': 0,
               'fumblelost': 0
    },
    'punt': {'no': 0,
             'yds': 0,
             # 'long': 0,
             'blkd': 0,
             'tb': 0,
             'fc': 0,
             'plus50': 0,
             'inside20': 0,
             'inside10': 0
             # 'avg': 0
    },
    'pr': {'no': 0,
           'yds': 0,
           'td': 0
           # 'long': 0
    },
    'block': {'no': 0},
    'ko': {'no': 0,
           'yds': 0,
           'ob': 0,
           'tb': 0,
           'fc': 0
           # 'fcyds': 0,
           # 'ona': 0,
    },
    'kr': {'no': 0,
           'yds': 0,
           'td': 0
           # 'long': 0
    },
    'fga': {'att': 0,
            'good': 0,
            'bad': 0,
            'blkd': 0},
    # 'hold': {'no': 0},
    'patkick': {'att': 0,
                'good': 0,
                'bad': 0},
    'patrush': {
        'att': 0, 'good': 0, 'bad': 0},
    'patpass': {
        'att': 0, 'good': 0, 'bad': 0},
    'tackle': {'no': 0,
               'tackua': 0,
               'tacka': 0},
    'score': {'att': 0,
              'pts': 0},
    'penalties': {'no': 0,
                  'yds': 0},
    # derived/rare stats currently hidden
    'conversions': {'thirdconv': 0,
                    'thirdatt': 0,
                    'fourthconv': 0,
                    'fourthatt': 0
    },
    'misc': {'yds': 0,
             # 'top': 0,
             'ona': 0,
             'onm': 0}
             # 'ptsto': 0},
    # 'firstdowns': {'no': 0,
    #                'rush': 0,
    #                'pass': 0,
    #                'penalty': 0},
    # 'redzone': {'att': 0,
    #             'scores': 0,
    #             'points': 0,
    #             'tdrush': 0,
    #             'tdpass': 0,
    #             'fgmade': 0,
    #             'endfga': 0,
    #             'enddowns': 0,
    #             'endint': 0,
    #             'endfumb': 0,
    #             'endhalf': 0,
    #             'endgame': 0},
}

with open('Data Models/loop_2_empty_player_agg_stats.json', 'w') as file:
    json.dump(empty_player_agg_stats, file)

print('empty player agg stats are updated on {}\n'.format(now))


# -------------------------------------------------------------------------------------

'''
For the new approach of role matching
'''

role_team_model = {
    'punter': "offense",
    'rusher': "offense",
    'passer': "offense",
    'receiver': "offense",
    'fgattempter': "offense",
    'kicker': "offense",
    'patkicker': "offense",
    'blocker': "defense",
    'returner': "defense",
    'recover': "unsure",
    'breaker': "defense",
    'sacker': "defense",
    'tackler': "defense",
    'faker': "offense",
    'intercepter': "defense",
    'holder': "offense"}

with open('Data Models/role_team_model.json', 'w') as file:
    json.dump(role_team_model, file)

print('Role_team_model is updated on {}\n'.format(now))
