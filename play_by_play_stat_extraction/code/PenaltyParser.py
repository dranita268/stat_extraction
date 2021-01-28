import re
from nltk.tokenize import word_tokenize

general_penalty_identifiers = [r'\bpen\.*\b', r'penal[izedty]{2,4}', r'illegal[ly]{0,2}',  r'\bill\.*\b',
                               r'\bfoul\b', r'\binterfer[enced]{0,4}\b', r'violation']

pen_results = {
        'declined': [r'decline[sd]{0,1}'],
        'refused': [r'refuse[sd]{0,1}'],
        'offset': [r'offset[stinged]{0,4}']
    }

penalty_types = {
    'back field in motion': {'inplay': 'presnap',
                             'team': 'offense',
                             'line of measurement': 'LOS',
                             'yards': 5,
                             'down': 0,
                             'identifiers': [r'back field in motion'],
                             'offsettable': False,
                             'declinable': True},
    'clipping': {'inplay': 'inplay',
                 'team': 'offense',
                 'line of measurement': 'SOF',
                 'yards': 15,
                 'down': 0,
                 'identifiers': [r'\bclip[pedings]{1,4}\b'],
                 'offsettable': True,
                 'declinable': True},
    'delay of game': {'inplay': 'presnap',
                      'team': 'offense',
                      'line of measurement': 'LOS',
                      'yards': 5,
                      'down': 0,
                      'identifiers': [r'delay[seding]{0,3}'],
                      'offsettable': False,
                      'declinable': True},
    'encroachment': {'inplay': 'presnap',
                     'team': 'offense',
                     'line of measurement': 'LOS',
                     'yards': 5,
                     'down': 0,
                     'identifiers': [r'encroach[sedmenting]{0,4}'],
                     'offsettable': False,
                     'declinable': True},
    'face mask': {'inplay': 'inplay',
                  'team': 'defense',
                  'line of measurement': 'SOF',
                  'yards': 15,
                  'down': 1,
                  'identifiers': [r'face *mask'],
                  'offsettable': True,
                  'declinable': True},
    'fair catch interference': {'inplay': 'inplay',
                                'team': 'special teams',
                                'line of measurement': 'unsure',
                                'yards': 15,
                                'down': 1,
                                'identifiers': [r'interfere[nced]{1,3}', r'fair catch interfere[nced]{1,3}'],
                                'offsettable': True,
                                'declinable': True},
    'fair catch violation': {'inplay': 'inplay',
                             'team': 'special teams',
                             'line of measurement': 'SOF',
                             'yards': 5,
                             'down': 0,
                             'identifiers': [r'fair catch.*violat'],
                             'offsettable': True,
                             'declinable': True},
    'false start': {'inplay': 'presnap',
                    'team': 'offense',
                    'line of measurement': 'LOS',
                    'yards': 5,
                    'down': 0,
                    'identifiers': [r'false start'],
                    'offsettable': False,
                    'declinable': True},
    'helmet to helmet collision/targeting': {'inplay': 'inplay',
                                             'team': 'defense',
                                             'line of measurement': 'SOF',
                                             'yards': 15,
                                             'down': 1,
                                             'identifiers': ['helmet[ -]*to[ -]*helmet'],
                                             'offsettable': True,
                                             'declinable': True},
    'helping runner': {'inplay': 'inplay',
                       'team': 'offense',
                       'line of measurement': 'unsure',
                       'yards': 5,
                       'down': 0,
                       'identifiers': [r'helping *runner'],
                       'offsettable': True,
                       'declinable': True},
    'holding': {'inplay': 'inplay',
                'team': 'unsure',
                'line of measurement': 'unsure',
                'yards': 10,
                'down': 0,
                'identifiers': [r'holding'],
                'offsettable': True,
                'declinable': True},
    # Special treatment for holding

    'horse collar tackle': {'inplay': 'inplay',
                            'team': 'defense',
                            'line of measurement': 'SOF',
                            'yards': 15,
                            'down': 1,
                            'identifiers': [r'horse collar'],
                            'offsettable': True,
                            'declinable': True},
    'illegal block': {'inplay': 'inplay',
                      'team': 'offense',
                      'line of measurement': 'unsure',
                      'yards': 10,
                      'down': 0,
                      'identifiers': [r'block'],
                      'offsettable': True,
                      'declinable': True},
    # block overlap with action block

    'illegal formation': {'inplay': 'presnap',
                          'team': 'offense',
                          'line of measurement': 'LOS',
                          'yards': 5,
                          'down': 0,
                          'identifiers': [r'formation'],
                          'offsettable': False,
                          'declinable': True},
    'illegal forward pass': {'inplay': 'inplay',
                             'team': 'offense',
                             'line of measurement': 'LOS',
                             'yards': 5,
                             'down': 0,
                             'identifiers': [r'(?:illegal) *forward pass[seding]'],
                             'offsettable': True,
                             'declinable': True},
    'illegal helmet contact': {'inplay': 'inplay',
                               'team': 'unsure',
                               'line of measurement': 'unsure',
                               'yards': 15,
                               'down': 1,
                               'identifiers': [r'helmet contact'],
                               'offsettable': True,
                               'declinable': True},
    'illegal kicking': {'inplay': 'inplay',
                        'team': 'unsure',
                        'line of measurement': 'SOF',
                        'yards': 5,
                        'down': 0,
                        'identifiers': [r'illegal kicking'],
                        'offsettable': True,
                        'declinable': True},
    'illegal motion': {'inplay': 'presnap',
                       'team': 'offense',
                       'line of measurement': 'LOS',
                       'yards': 5,
                       'down': 0,
                       'identifiers': [r'\bmotion\b'],
                       'offsettable': False,
                       'declinable': True},
    'illegal participation/substitution': {'inplay': 'presnap',
                                           'team': 'unsure',
                                           'line of measurement': 'LOS',
                                           'yards': 5,
                                           'down': 0,
                                           'identifiers': ['illegal (?:participation|substitution)'],
                                           'offsettable': False,
                                           'declinable': True},
    'illegal procedure': {'inplay': 'presnap',
                          'team': 'offense',
                          'line of measurement': 'LOS',
                          'yards': 5,
                          'down': 0,
                          'identifiers': [r'ill.*proc(?:edure)\.*', r'procedure'],
                          'offsettable': False,
                          'declinable': True},
    'illegal shift': {'inplay': 'presnap',
                      'team': 'offense',
                      'line of measurement': 'LOS',
                      'yards': 5,
                      'down': 0,
                      'identifiers': [r'illegal shift'],
                      'offsettable': False,
                      'declinable': True},
    'illegal touching': {'inplay': 'inplay',
                         'team': 'offense',
                         'line of measurement': 'LOS',
                         'yards': 5,
                         'down': 0,
                         'identifiers': [r'illegal touch'],
                         'offsettable': True,
                         'declinable': True},
    'illegal use of hands': {'inplay': 'inplay',
                             'team': 'unsure',
                             'line of measurement': 'LOS',
                             'yards': 10,
                             'down': 0,
                             'identifiers': [r'use of hands'],
                             'offsettable': True,
                             'declinable': True},
    'ineligible downfield on pass': {'inplay': 'inplay',
                                     'team': 'offense',
                                     'line of measurement': 'LOS',
                                     'yards': 5,
                                     'down': 0,
                                     'identifiers': [r'ineligible downfield'],
                                     'offsettable': True,
                                     'declinable': True},
    'kick catching interference': {'inplay': 'inplay',
                                   'team': 'special teams',
                                   'line of measurement': 'SOF',
                                   'yards': 15,
                                   'down': 0,
                                   'identifiers': [r'kick.*interf[erenced]+'],
                                   'offsettable': True,
                                   'declinable': True},
    'kickoff out of bounds': {'inplay': 'inplay',
                              'team': 'special teams',
                              'line of measurement': 'LOS',
                              'yards': 5,
                              'down': 1,
                              'identifiers': [r'kick.* out of bounds'],
                              'offsettable': False,
                              'declinable': True},
    # overlapping with OOB result
    'noncontact foul': {'inplay': 'inplay',
                        'team': 'unsure',
                        'line of measurement': 'SOF',
                        'yards': 15,
                        'down': 1,
                        'identifiers': [],
                        'offsettable': True,
                        'declinable': True},
    'offside': {'inplay': 'presnap',
                'team': 'defense',
                'line of measurement': 'LOS',
                'yards': 5,
                'down': 0,
                'identifiers': [r'offside'],
                'offsettable': False,
                'declinable': True},
    'pass interference': {'inplay': 'inplay',
                          'team': 'unsure',
                          'line of measurement': 'unsure',
                          'yards': 15,
                          'down': 1,
                          'identifiers': [r'interfere[nced]{1,3}', r'pass interfere[nced]{1,3}'],
                          'offsettable': True,
                          'declinable': True},
    'personal foul': {'inplay': 'unsure',
                      'team': 'unsure',
                      'line of measurement': 'SOF',
                      'yards': 15,
                      'down': 1,
                      'identifiers': [r'per\.*[sonal]* *foul'],
                      'offsettable': True,
                      'declinable': True},
    'piling on': {'inplay': 'postplay',
                  'team': 'unsure',
                  'line of measurement': 'SOF',
                  'yards': 15,
                  'down': 1,
                  'identifiers': [r'piling on'],
                  'offsettable': True,
                  'declinable': True},
    'player disqualification': {'inplay': 'N',
                                'team': 'unsure',
                                'line of measurement': 'LOS',
                                'yards': 15,
                                'down': 1,
                                'identifiers': [r'(?:player) *disqualification'],
                                'offsettable': False,
                                'declinable': False},
    'roughing the holder': {'inplay': 'inplay',
                            'team': 'defense',
                            'line of measurement': 'LOS',
                            'yards': 15,
                            'down': 1,
                            'identifiers': [r'rough[seding]{0,3} (?:the)* *holder'],
                            'offsettable': True,
                            'declinable': True},
    'roughing the kicker': {'inplay': 'inplay',
                            'team': 'defense',
                            'line of measurement': 'LOS',
                            'yards': 15,
                            'down': 1,
                            'identifiers': [r'rough[seding]{0,3} (?:the)* *kicker'],
                            'offsettable': True,
                            'declinable': True},
    'roughing the passer': {'inplay': 'unsure(In-Play/Post-Play)',
                            'team': 'defense',
                            'line of measurement': 'LOS',
                            'yards': 15,
                            'down': 1,
                            'identifiers': [r'rough[seding]{0,3} (?:the)* *passer'],
                            'offsettable': True,
                            'declinable': True},
    'substitution infraction': {'inplay': 'presnap',
                                'team': 'unsure',
                                'line of measurement': 'LOS',
                                'yards': 5,
                                'down': 0,
                                'identifiers': [r'substitution infraction'],
                                'offsettable': False,
                                'declinable': True},
    'too many on the field': {'inplay': 'presnap',
                              'team': 'unsure',
                              'line of measurement': 'LOS',
                              'yards': 5,
                              'down': 0,
                              'identifiers': [r'too many'],
                              'offsettable': False,
                              'declinable': True},
    'too much time': {'inplay': 'presnap',
                      'team': 'unsure',
                      'line of measurement': 'LOS',
                      'yards': 5,
                      'down': 0,
                      'identifiers': [r'too much time'],
                      'offsettable': False,
                      'declinable': True},
    'tripping': {'inplay': 'inplay',
                 'team': 'unsure',
                 'line of measurement': 'unsure',
                 'yards': 15,
                 'down': 1,
                 'identifiers': [r'\btrip[pseding]{0,4}\b'],
                 'offsettable': True,
                 'declinable': True},
    'unsportsmanlike conduct': {'inplay': 'N',
                                'team': 'unsure',
                                'line of measurement': 'LOS',
                                'yards': 15,
                                'down': 1,
                                'identifiers': [r'unsportsmanlike'],
                                'offsettable': True,
                                'declinable': True}}


identifiers = general_penalty_identifiers.copy()
for k in penalty_types.keys():
    identifiers += penalty_types.get(k).get('identifiers')


class PenaltyParser:  # parse for penalty information on line level


    def __init__(self, twoline_obj):
        self.line = twoline_obj.text
        self.game = twoline_obj.game
        self.exist = False
        self.penalty_start = None
        self.penalty_text = self.line
        self.penalty_info = None
        self.penalty_alert = []
        self.teams = {'offense': twoline_obj.poss,
                      'defense': [t for t in self.game.team_abbreviations if t != twoline_obj.poss][0]}


    def check_existence_and_isolate_penalty_text(self):
        exist = False
        penalty_text = None
        identifiers_found = [re.search(p, self.line) for p in identifiers]
        if any(identifiers_found):
            exist = True
            identifiers_found = [i for i in identifiers_found if bool(i)]
            earliest_identifier = sorted(identifiers_found, key=lambda x: x.span()[0])[0]
            self.penalty_start = earliest_identifier.span()[0]
            penalty_text = self.line[self.penalty_start:]
        self.penalty_text = penalty_text
        self.exist = exist
        # return exist, penalty_text


    def tag_teams(self):
        teams = list(self.teams.values()) + [self.game.h, self.game.v]
        line = re.sub(r'<name .+?>','',self.penalty_text)
        tagged_line = self.penalty_text
        for t in set(word_tokenize(line)):
            if any([re.search(r'\b{}\b'.format(x), t) for x in teams]):
                tagged_line = re.sub(r'\b{}\b'.format(t), '<team {}>'.format(t), tagged_line)
        self.penalty_text = tagged_line
        # return tagged_line


    @staticmethod
    def tag_yards(penalty_text):
        tagged_text = penalty_text
        yards = r'(?:5|10|15) (?:yards*|yds*\.*)'
        for y in re.findall(yards,penalty_text):
            tagged_text = re.sub(y, '<yard {}>'.format(y), tagged_text)
        return tagged_text


    def match_penalty_type(self):
        types_found = []
        for k in penalty_types.keys():
            pen_type = k
            type_identifiers = penalty_types.get(k).get('identifiers')
            type_exist = any([re.search(p, self.line) for p in type_identifiers])
            if type_exist:
                # special double-check for penalty types with overlapping/misleading identifiers with a non-penalty action
                if k in ['delay of game', 'holding',
                         'illegal block', 'kickoff out of bounds', 'tripping']:
                    if any([re.search(i, self.line) for i in general_penalty_identifiers]):
                        types_found.append(pen_type)
                    else:
                        self.exist = False
                        self.penalty_alert.append("Possibly ambiguous penalty identifier")

                # special double-check for pass/fc/kickoff catch interference, which share the identifier 'interefere'
                elif 'interference' in k:
                    cases = {'pass': 'pass interference',
                             'fair catch': 'fair catch interference',
                             'kick catch': 'kick catching interference'}
                    for case in cases.keys():
                        if case in self.penalty_text:
                            types_found.append(cases.get(case))

                else:
                    types_found.append(pen_type)

        types_found = list(set(types_found))
        if len(types_found) > 0:
            return types_found


    def match_penalty_results(self, pen_types_found):
        pen_result = []
        for k in pen_results:
            temps = pen_results.get(k)
            if any([re.search(t, self.line) for t in temps]):
                pen_result.append(k)
        if 'offset' in pen_result:
            # if any "offset" is matched, all penalty types found are offset
            return ['offset']*len(pen_types_found)

        if pen_result and not pen_types_found:
            self.penalty_alert.append("Can't match penalty type")
            return pen_result
        if not pen_types_found and not pen_result:
            self.penalty_alert.append("Can't match penalty type")
            return ['valid']

        if pen_types_found and len(pen_result) < len(pen_types_found):
            # If multiple types of penalty in one line, maybe the first one is declined (explicit)
            # and the last one is valid (omitted)
            # and if no offsetting/decline/refuse then default penalty is valid and effective
            return pen_result + ["valid"]
        elif pen_types_found and pen_result and len(pen_result) == len(pen_types_found):
            return pen_result
        else:
            self.penalty_alert.append("Ambiguous result")


    def extract_penalty_effects(self, pen_type, result):  # team penalized and yards penalized
        # match for team:
        team_found = re.search(r'<team .+?>', self.penalty_text)
        if team_found:
            team = team_found.group()[5:-1].strip()
        else:
            team_rule = penalty_types.get(pen_type).get('team')
            if team_rule == 'unsure':
                team = team_rule
            elif team_rule == 'special teams':
                team = 'special teams'
            else:
                team = self.teams.get(team_rule)

        if result == 'valid':
            # match for yards
            yard_found = re.search(r'<yard .+?>', self.penalty_text)
            if yard_found:
                yards = int(re.search(r'[510]{1,2}', yard_found.group()[5:-1].strip()).group())
            else:
                yards = penalty_types.get(pen_type).get('yards')
        else:
            yards = 0  # if offset of declined penalty, yards penalized = 0
        return team, yards


    def gather_penalty_info(self):  # assuming one type of penalty can only happen once in a single play
        self.check_existence_and_isolate_penalty_text()
        pen_types_found = self.match_penalty_type()

        if self.exist:
            self.tag_teams()

            self.penalty_text = self.tag_yards(self.penalty_text)
            self.penalty_info = {'penalty text': self.penalty_text,
                                 'penalty info': {}}
            pen_results_found = self.match_penalty_results(pen_types_found)

            for i in range(len(pen_results_found)):
                pr = pen_results_found[i]  # pr: penalty result
                try:
                    pt = pen_types_found[i]  # pt: penalty type
                    pen_effect = self.extract_penalty_effects(pt, pr)
                    self.penalty_info.get('penalty info').update({
                        pt: {
                            'result': pr, 'team': pen_effect[0], 'yards': pen_effect[1],
                            'lom': penalty_types.get(pt).get('line of measurement'),
                            'down change': penalty_types.get(pt).get('down')}})
                except TypeError:
                    pt = 'unknown type'
                    team_found = re.search(r'<team .+?>', self.penalty_text)
                    if team_found:
                        team = team_found.group()[5:-1].strip()
                    else:
                        team = "unsure"
                    yard_found = re.search(r'<yard .+?>', self.penalty_text)
                    if yard_found:
                        yard = yard_found.group()[5:-1].strip()
                    else:
                        yard = "unsure"
                    self.penalty_info.get('penalty info').update({
                        pt: {
                            'result': pr, 'team': team, 'yards': yard,
                            'lom': "unknown",
                            'down change': "unknown"}})

            return self.penalty_info


'''
Out of 12 games and 3209 lines, 90 lines were found as penalties, which is 2.8%. 
On average, it finds 7 sentences as penalty in each game.
defensive holding               19
illegal procedure               14
offside                         14
personal foul                    7
delay of game                    6
ineligible downfield on pass     5
illegal block                    4
illegal motion                   3
clipping                         3
tripping                         3
roughing the kicker              2
kickoff out of bounds            2
illegal shift                    2
face mask                        2
roughing the passer              2
illegal use of hands             2
'''
