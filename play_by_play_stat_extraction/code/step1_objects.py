import re
import pandas as pd
import nltk
import json
import xlsxwriter
import nameparser
import os
from tqdm import tqdm
from fuzzywuzzy import process
from nltk.tokenize import word_tokenize
import jellyfish
from player_matching.player_name_matcher import PlayerNameMatcher
from player_matching.team_master_provider import TeamMasterProvider
from PlayerRoleMapper import PlayerRoleMapper


with open('Data Models/sentence_pattern_model.json', 'r') as j:
    sentence_pattern_model = json.loads(j.read())

with open('Data Models/matching_tuple_dict.json', 'r') as f:
    matching_tuple_dict = json.loads(f.read())

with open('Data Models/football_name_stopwords.txt', 'r') as file:
    football_nonnames = [re.compile(r"\b{}\b".format(item)) for item in file.read().split('@')]

action_dict_step1 = sentence_pattern_model.get('actions')
result_dict = sentence_pattern_model.get('results')

# exhaustive collection of context templates
# here template 2 is the same as 1, 4 is the same as 3. can be used to identify change in possession
context_regex_dict = {
    'template1': r'^[1234lso][ \t\-\,/]*([0123456789Gglsoa]{1,4}|goal)[ \t\-\,/]*(?:[A-Za-z]{1,4}[ \t\-\,/]*[0-9ls]{1,2}o*|50)',
    # 1-10-P23; 1-10-p-23
    'template2': r'^[A-Z|a-z]{1,4}[ \t\-\,/]{1,}[1234lso][ \t\-\,/]{1,}([0123456789Gglsoa]{1,4}|goal)[ \t\-\,/]{1,}(?:[A-Z|a-z]{1,4}[ \t\-\,/]*[0123456789lsoa]{1,4}|50)',
    # Pur 1-10-P23; pur 1-10-p-23
    'template3': r'^(?:50|[A-Z|a-z]{1,4}[ \t\-\,/]*[0-9ls]{1,2}o*)[ \t\-\,/]{1,}[1234lso][ \t\-\,/]{1,}([0123456789Gglsoa]{1,4}|goal)',  # P23-1-10
    'template4': r'^[A-Z|a-z]{1,4}[ \t\-\,/]{1,}(?:50|[A-Z|a-z]{1,4}[ \t\-\,/]*[0-9ls]{1,2}o*)[ \t\-\,/]{1,}[1234lso][ \t\-\,/]{1,}([0123456789Gglsoa]{1,4}|goal)',
    # Pur P23-1-10; P P23 1-GOAL
    'template5': r'^[1234lso] +([0123456789Gglsoa]{1,4}|goal) +(?:50|[A-Za-z]{1,} *[0-9ls]{1,2}o*)',
    # 1 10 P23; 1  10 P23; 1 10 p 23
    'template6': r'^[A-Z|a-z]{1,4}[ \t\-\,/]{1,}[1234lso] {1,}([0123456789Gglsoa]{1,4}|goal) {1,}(?:50|[A-Z|a-z]{1,4}[ \t\-\,/]*[0123456789lso]{1,2})',
    # Pur 1 10 P23
    'template7': r'^(?:50|[A-Z|a-z]{1,4}[ \t\-\,/]*[0-9ls]{1,2}o*) {1,}[1234lso] {1,}([0123456789Gglsoa]{1,4}|goal)',
    # P23 1 10
    'template8': r'^[A-Z|a-z]{1,4}[ \t\-\,/]{1,}(?:[A-Z|a-z]{1,4} ?[0-9ls]{1,2}o*|50) {1,}[1234lso] {1,}([0123456789Gglsoa]{1,4}|goal)',
    # Pur P23 1 10,
    'template9': r'^(?:50|[A-Za-z]{1,}[ \t\-/]*[0-9ls]{1,2}o*)[ \t\-/]*[1234lso][ \t\-/]*([0123456789Gglsoa]{1,4}|goal)',
    # ps-21 1-10
    'template10': r'^[1234lso][ \t\-\,/]*([0123456789Gglsoa]{1,4}|goal)[ \t\-\,/]*(?:[0-9ls]{1,2}o*[ \t\-\,/]*[A-Za-z]{1,}|50)',
    # 2-3-45a
}

# quarters synonym dictionary
quarters = {1: ['first', '1st'], 2: ['second', '2nd'], 3: ['third', '3rd'], 4: ['fourth', '4th']}

Sentence_Type_dict = {}
for k in sentence_pattern_model.get('actions').keys():
    d = sentence_pattern_model.get('actions').get(k)
    templates = []
    for kk in d.keys():
        templates += d.get(kk)
    Sentence_Type_dict.update({k: templates})
Sentence_Type_dict.update({'META': [r'\b(meta)\b']})


'''
Game Object for Loop 1
'''


class OneGame:
    
    def __init__(self, h, v, year):
        self.path = 'Jaisys_raw_games/round 7/' + ' '.join([h, "vs", v, str(year)]).title() + '.txt'  # change this when launching in production
        self.raw_game = self.readFile()  # this is a list of unprocessed lines
        self.length = len(self.raw_game)
        self.lines = []
        self.problem_lines = []
        self.v = v.lower()
        self.h = h.lower()
        self.year = str(year)
        self.h_roster = self.get_roster(self.h)
        self.v_roster = self.get_roster(self.v)
        self.game_df = pd.DataFrame()


    def __str__(self):
        return '_'.join([self.h, self.v, self.year])


    def __len__(self):
        return self.length


    def readFile(self):
        path = self.path
        file = open(path, 'r').read()
        file = file.split('\n')
        file = [line for line in file if len([i for i in line if i.isalpha() or i.isdigit()]) > 0]  # empty lines ignored

        s, e = 0, 0
        for i in range(len(file)):
            if ('game title' in file[i].lower() or 'team 1: ' in file[i].lower()) and\
                    'letter or text used to identify field side' not in file[i].lower():
                s = i
            if 'possession start must have "possession" + team possession format":' in file[i].lower() or\
                    'context format [poss-down-ytg-spotside-spot]'.replace(" ", "") in file[i].lower().replace(" ", ""):
                e = i
                break

        for i in range(s, e+1):
            file[i] += ' (meta)'
        return file


    def get_roster(self, team):
        # assuming players are always addressed in the play-by-play by last names
        # school name in title form and space inbetween school and self.year
        try:  # for games for which roster are stored in excel spreadsheets
            roster = pd.read_excel('Rosters/{}.xlsx'.format(' '.join([team.title(), str(self.year)])))
            # I also want to convert class (now: fr, so, jr, sr) into the year a player get into college'
            for i in roster.index:
                name = roster.at[i, 'Name']
                parsed_name = nameparser.HumanName(name)
                if parsed_name.last == "":  # must have last name. if cannot find, use first name as last name
                    parsed_name.last = parsed_name.first
                    parsed_name.first = ""
                # roster.at[i, 'First'] = parsed_name.first
                # roster.at[i, 'Middle'] = parsed_name.middle
                roster.at[i, 'Last'] = parsed_name.last  # roster.at[i, 'Suffix'] = parsed_name.suffix

            # Fake the jersey number: use the index of the player in the roster df as Jersey Number for the moment
            if roster['Jersey Number'].isnull().all() == True:
                roster['Jersey Number'] = [str(i) for i in roster.index.tolist()]
            roster['Jersey Number'] = [str(j) for j in roster['Jersey Number']]
            roster['Season'] = str(self.year)
            roster['Team'] = team
            roster['Player_id'] = ['-'.join(roster.loc[i, ['Season', 'Team', 'Jersey Number']]) for i in roster.index]

            # find players in the same roster with the same last names
            # problematic_names = roster['Last'].value_counts().loc[roster['Last'].value_counts() > 1,].index
            # roster['Problems'] = ['player with same last name exists' * bool(n in problematic_names) for n in
            #                       roster['Last']]
            roster = roster[['Name', 'Last', 'Position', 'Jersey Number', 'Class', 'Player_id']]

        except:  # for the games with active roster MongoDB Collection available
            matcher = PlayerNameMatcher(team.title(), int(self.year), 'MFB')
            code = matcher._get_team_code()
            roster_dict = matcher._get_active_players(code, int(self.year), 'MFB')

            if roster_dict != {}:
                roster = pd.DataFrame()
                roster['Name'] = [roster_dict.get(k).player_name for k in roster_dict.keys()]
                roster['Last'] = [roster_dict.get(k).player_name.split(",")[0] for k in roster_dict.keys()]
                roster['Position'] = [roster_dict.get(k).pos for k in roster_dict.keys()]
                roster['Jersey Number'] = [roster_dict.get(k).jersey_number for k in roster_dict.keys()]
                roster['Class'] = [roster_dict.get(k).player_class for k in roster_dict.keys()]
                roster['Player_id'] = [roster_dict.get(k).player_uuid for k in roster_dict.keys()]
            else:
                raise NameError('Roster for {} {} is not found'.format(team.title(), self.year))

        return roster  # a df used in match_players function.


    def process_one_line(self, index):
        line = OneLine(self, index)
        line.pre_process()
        line.get_context()
        line.fix_context_typo()
        line.get_sentence_type()
        line.deduct_action_from_name()
        line.deduct_passing_result()
        line.get_parentname()
        line.update_poss()

        self.lines.append(line)
        return line


    def format_and_output(self):
        df = pd.DataFrame()
        df['index'] = [l.index for l in self.lines]
        df['processed raw'] = [l.processed_raw for l in self.lines]
        df['context'] = [l.beginning_context for l in self.lines]
        df['poss'] = [l.poss for l in self.lines]
        df['sentence_type'] = [l.sentence_type for l in self.lines]
        df['ParentName'] = [l.ParentName for l in self.lines]
        df['allow_continuation'] = [l.allow_continuation for l in self.lines]
        df['continuation action'] = [l.continuation_actions for l in self.lines]
        df['continuation result'] = [l.continuation_results for l in self.lines]
        df['dirty raw'] = [l.raw for l in self.lines]

        self.game_df = df
        output_path = 'loop1 output' + '/{}.xlsx'.format(' '.join([self.h, "vs", self.v, str(self.year)]).title())
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='loop1a', index=False)
        workbook = writer.book
        worksheet = writer.sheets['loop1a']

        # col width
        def fit_width(col, hide=False, col_format={}):
            colname = df.columns[col]
            best_fit = max([len(str(x)) for x in df[colname].tolist() + [colname]])
            worksheet.set_column(first_col=col, last_col=col, width=best_fit, cell_format=col_format,
                                 options={'hidden': hide})

        for c in range(len(df.columns)):
            fit_width(c)
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, {})
        writer.save()


    def analyse_game(self):
        print('Step 1: ', self)
        for i in tqdm(range(self.length)):
            try:
                self.process_one_line(i)
            except:
                self.lines.append(OneLine(self, i))
                self.problem_lines.append(OneLine(self, i))
        self.format_and_output()
        print("Sentence categorizing finished with {} problematic sentences".format(len(self.problem_lines)))


"""
-------------------------------------------------------------------------------------
Line Object for Loop 1
"""


class OneLine:
    
    def __init__(self, onegame, ind):
        self.index = ind
        self.game = onegame
        self.raw = self.game.raw_game[ind]  # unprocessed from the text file
        self.processed_raw = self.raw
        self.beginning_context = self.get_context()[0]  # look for context
        self.context_regex_key = self.get_context()[1]  # template / format of the context
        self.text = self.get_context()[2]  # preprocessed raw with context removed
        self.named_line = self.text

        self.poss = None
        self.parsed_beginning_context = self.parse_context(self.beginning_context)
        self.sentence_type = None
        self.ParentName = None
        self.allow_continuation = None
        self.continuation_actions = None
        self.continuation_results = None
        self.penalty_info = None

        self.sentence_type_alert = None
        self.pn_arena = None


    def __str__(self):
        return '\n'.join([self.raw, self.sentence_type, self.ParentName])


    def pre_process(self):
        text = self.text
        processed_text = text.replace('\t', ' ').replace('- ', '-').replace(' -', '-')
        processed_text = processed_text.replace('--', ' ').replace('_', ' ').replace('  ', ' ')
        processed_text = processed_text.strip()
        processed_text = processed_text.replace('1t', 'lt').replace('1g', 'lg').replace('1e', 'le')
        processed_text = re.sub(r'\bl *st\b', '1st', processed_text)  # a common typo mistaking 1 and l

        # convert all ordinal numbers and text numbers in a line into cardinal number
        import json
        with open('Data Models/numbers.json', 'r') as fp:
            numbers_d = json.load(fp)

        broken = processed_text.lower().split(' ')
        for i in range(len(broken)):
            for k in numbers_d.keys():
                chunk = ''.join([x for x in broken[i] if x.isalpha() or x.isdigit()])
                if chunk in numbers_d.get(k):
                    broken[i] = str(k)
        processed_text = ' '.join(broken)
        processed_text = re.sub(r'\bno good\b', 'nogood', processed_text)

        # replace all team nicknames with the standard team name used to identify the game
        team_provider = TeamMasterProvider()
        nicknames = {t: team_provider.get_team_data_from_master(t.title(), None, None)['teamNickNames']
                     for t in [self.game.h, self.game.v]}
        for t in nicknames.keys():
            for nickname in nicknames.get(t):
                processed_text = re.sub(r"\b{}\b".format(nickname.lower()), t, processed_text)
        self.processed_raw = self.beginning_context+" "+processed_text  # all in lower case
        return self.processed_raw


    @staticmethod
    def ptnmatcher(d, x):  # x is the string to be matched
        out = []
        import re
        for k in d.keys():
            temps = d.get(k)
            match_bools = [bool(re.search(temp, x)) for temp in temps]
            # match_bools = []
            # for temp in temps:
            #     print(temp)
            #     match_bools.append(bool(re.search(temp, x)))
            if any(match_bools):
                out.append(k)
        return out


    @staticmethod
    def parse_context(context, context_format='poss down-tyg spotside-spot'):  # [POSS-DOWN-YTG-SPOTSIDE-SPOT]
        context = context.replace("goal", "g")
        error = ''
        if len(re.split(r'[ \t\-,/]', context)) < 4:
            error = 'context structure error'

        try:
            rest = context

            spot = re.search(r'(?:[A-Za-z]{1,3}[ \t\-\,/]*[0-9lso]{1,2}|50)$', context)
            spot_text = spot.group()
            rest = rest[:spot.span()[0]]

            if spot_text != '50':
                spotside = re.search(r'[a-zA-Z]{1,3}', spot_text)
                spotside_text = spotside.group()
                spotnum_text = spot_text[spotside.span()[1]:]
            else:
                spotside_text = ''
                spotnum_text = spot_text

            poss = re.search(r'^[a-zA-Z]{1,3}', rest)
            poss_text = poss.group()
            rest = rest[poss.span()[1]:]

            down = re.search(r'[1234l]', rest)
            down_text = down.group()

            ytg_text = rest[down.span()[1]:]

            poss_text = ''.join([t for t in poss_text if t.isdigit() or t.isalpha()])
            down_text = ''.join([t for t in down_text if t.isdigit() or t.isalpha()])
            ytg_text = ''.join([t for t in ytg_text if t.isdigit() or t.isalpha()])
            spotside_text = ''.join([t for t in spotside_text if t.isdigit() or t.isalpha()])
            spotnum_text = ''.join([t for t in spotnum_text if t.isdigit() or t.isalpha()])

            if any([char.isalpha() for char in down_text]):
                down_text = down_text.lower().replace('l', '1').replace('s', '5').replace('o', '0')
                error = 'Character misrecognition'
            if any([char.isalpha() for char in ytg_text if char != 'g']):  # ytg should be only numbers or g for goal
                ytg_text = ytg_text.lower().replace('l', '1').replace('s', '5').replace('o', '0')
                error = 'Character misrecognition'
            if any([char.isalpha() for char in spotnum_text]):
                spotnum_text = spotnum_text.lower().replace('l', '1').replace('s', '5').replace('o', '0')
                error = 'Character misrecognition'

        except AttributeError:
            poss_text, down_text, ytg_text, spotside_text, spotnum_text = '', '', '', '', ''
            error = 'context order error'

        return poss_text, down_text, ytg_text, spotside_text, spotnum_text, error


    def get_context(self):
        # Returns a tuple (context, play_text)
        # get_context('I40-3-13 Allen\'s pass') -> ('I40-3-13', " Allen's pass")
        # get_context('IL I40-3-13 Allen\'s pass') -> ('IL I40-3-13', " Allen's pass")
        # get_context('3-13-I40 Allen\'s pass') -> ('3-13-I40', " Allen's pass")
        # get_context('IL 3-13-I40 Allen\'s pass') -> ('IL 3-13-I40', " Allen's pass")
        text = self.processed_raw.strip().lower()
        if text[0:15].count('/') >= 2:
            text = text.replace('/ ', '-').replace('/', '-')
        beginning_context = ""
        context_regex_key = ""
        for key in context_regex_dict.keys():
            regex = context_regex_dict.get(key)
            context = re.search(regex, text)

            if context:
                context_regex_key = key
                beginning_context = context.group()
                # context_regex = regex
                text = re.sub(regex, '', text).strip().replace("-", " ")
                break
            else:
                beginning_context = ""
        # context_regex = context_regex_dict.get(context_regex_key)
        if context_regex_key == 'template4':
            try:
                s = re.search(r'(?:50|[A-Z|a-z]{1,4}[ \\t\\-\\,/]*[0-9ls]{1,2}o*)', beginning_context).group()
                p, d, y = re.split(r'[ \t\-\,/]{1,}', beginning_context.replace(s, ""))
                beginning_context = '{} {}-{} {}'.format(p, d, y, s)
            except:
                pass
        return beginning_context, context_regex_key, text


    def fix_context_typo(self):
        poss_text, down_text, ytg_text, spotside_text, spotnum_text, error = self.parsed_beginning_context
        if self.beginning_context != "":
            # fix typo in beginning context
            self.beginning_context = poss_text + " " + down_text + "-" + ytg_text + " " + spotside_text + spotnum_text
        if self.parsed_beginning_context[3:5] == ('',"50"):
            spotside_text = OneLine(self.game, self.index-1).parsed_beginning_context[3]
            i = self.index
            while spotside_text == '':
                i = i-1
                spotside_text = OneLine(self.game, i).parsed_beginning_context[3]

            self.beginning_context = poss_text + " " + down_text + "-" + ytg_text + " " + spotside_text + spotnum_text
            self.parsed_beginning_context = self.parse_context(self.beginning_context)


    def get_sentence_type(self):
        # match for sentence type: scrim, nonscrim, gameheader, gamestatus
        raw = self.processed_raw
        context = self.beginning_context
        play_text = self.text
        sentence_type_matches = self.ptnmatcher(Sentence_Type_dict, play_text)
        if '(meta)' in self.raw:
            self.sentence_type = "META"
            return self.sentence_type

        if context != "" and len([c for c in context if c.isalpha() or c.isdigit()]) > 0:
            if len(sentence_type_matches) == 0:
                self.sentence_type_alert = 'have context but found no match with scrim keywords'
            sentence_type_matches = 'SCRIM'

        else:
            if any([bool(re.search(t, raw)) for t in Sentence_Type_dict.get('SCRIM')]):
                self.sentence_type_alert = 'Found scrim keywords but no context'

            if len(sentence_type_matches) != 0:
                if 'FieldGoal' not in self.ptnmatcher(action_dict_step1.get('SCRIM'), raw) and 'td' not in raw:
                    try:  # if no context never scrim
                        sentence_type_matches = [m for m in sentence_type_matches if m != 'SCRIM']
                    except ValueError:
                        pass
                sentence_type_matches = ",".join(sentence_type_matches)
            else:  # no context, no matched raw type
                sentence_type_matches = 'OTHERTEXT'  # no context and can't find a match in the sentence type dictionary
                if len(''.join([l for l in raw if l.isdigit() or l.isalpha()])) == 0:
                    sentence_type_matches = 'OTHERTEXT'

        if set(sentence_type_matches.split(',')) == {'SCRIM', 'NONSCRIM'}:
            # if raw text at least has context
            if 'return' in raw or 'penal' in raw or 'punt' in raw:  # correct for punt return, scrim penalty
                sentence_type_matches = 'SCRIM'
        if set(sentence_type_matches.split(',')) == {'SCRIM', 'GAMESTATUS'}:  # for fg/td with score in one line
            if 'FieldGoal' in self.ptnmatcher(action_dict_step1.get('SCRIM'), raw) or 'td' in raw:
                sentence_type_matches = 'SCRIM'
        if sentence_type_matches == '':
            sentence_type_matches = 'OTHERTEXT'

        if len([m for m in sentence_type_matches.split(',') if m not in ['GAMESTATUS', 'GAMEHEADER', 'OTHERTEXT']]) > 0:
            sentence_type_matches = ','.join(
                [m for m in sentence_type_matches.split(',') if m not in ['GAMESTATUS', 'GAMEHEADER', 'OTHERTEXT']])

        if 'kick' in raw and ',' in sentence_type_matches:  # for the naughty 'kick'
            if 'Complete' in self.ptnmatcher(result_dict, raw) or 'Incomplete' in self.ptnmatcher(result_dict, raw):
                sentence_type_matches = 'SCRIM'
            else:
                sentence_type_matches = ','.join([m for m in sentence_type_matches.split(',') if m != 'SCRIM'])

        if sentence_type_matches == 'SCRIM' and re.search(r'kick[sed]{1,2}', self.text):
            self.text = re.sub(r'kick[sed]{1,2}', 'punted', self.text)
        self.sentence_type = sentence_type_matches

        return sentence_type_matches


    def deduct_action_from_name(self):
        # find names from the text. The same as in loop 2
        roster = pd.concat([self.game.v_roster, self.game.h_roster])
        text = re.sub(r'{}|{}'.format(self.game.h, self.game.v), "", self.text)
        for s in football_nonnames:
            text = re.sub(s, '', text)
            text = re.sub(r'[0-9]', '', text).strip()
        for s in football_nonnames:
            # a second time removing stopwords in case of any left-behinds due to order in the list
            text = re.sub(s, '', text)
        tokens = [t for t in word_tokenize(text) if
                  t.replace("'", "").replace(".", "").isalpha() and
                  len(t) >= min([len(last) for last in roster['Last']])]
        tokens = list(set(tokens))

        for t in tokens:
            possible = process.extract(t, roster['Last'])[0:2]  # the top 2 most possible names
            if possible[0][1] == 100:
                self.named_line = re.sub(r"\b{}\b".format(t), '<name {}>'.format(t), self.named_line)
            elif t.lower() in self.text and [
                x for x in nltk.word_tokenize(self.raw) if t.lower() in x.lower()][0].istitle():
                # the word should be capitalized in the original sentence to be considered a name
                self.named_line = re.sub(r"\b{}\b".format(t), '<name {}>'.format(t), self.named_line)
            elif possible[0][1] >= 85:# and jellyfish.jaro_winkler(t, possible[0][0].lower()) > 0.8:
                # t should at least have a spelling similarity of 85 to be considered as a name
                self.named_line = re.sub(r"\b{}\b".format(t), '<name {}>'.format(t), self.named_line)

        # match for possible pass/punt/kickoff with name to name pattern:
        if re.search(r'<name.+?>.+(?:to|intend[ed]{0,2} for|for) <name.+?>',self.named_line) and \
                self.sentence_type == 'SCRIM':
            pass_temps = sentence_pattern_model.get('actions').get('SCRIM').get('Pass')
            if re.search(r'<name.+?> complete[sed]{0,2} to', self.named_line):
                self.text = 'pass ' + self.text
                self.processed_raw = self.beginning_context + ' ' + self.text
                self.named_line = 'pass ' + self.named_line
            elif 'Punt' not in self.ptnmatcher(action_dict_step1.get('SCRIM'), self.named_line) and \
                    'kick' not in self.named_line and not any([re.search(p, self.text) for p in pass_temps]):
                self.text = 'pass ' + self.text
                self.processed_raw = self.beginning_context + ' ' + self.text
                self.named_line = 'pass ' + self.named_line
            elif 'Punt' in self.ptnmatcher(action_dict_step1.get('SCRIM'), self.named_line):
                first_name_found = re.findall(r'<name .+?>', self.named_line)[0][6:-1]
                self.text = self.text.replace(first_name_found, first_name_found+' punted')
                self.processed_raw = self.beginning_context + ' ' + self.text
                self.named_line = self.named_line.replace(first_name_found, first_name_found+' punted')

        # if re.search(r'<name.+?>.+(?:to|intend[ed]{0,2} for) <name.+?>', self.named_line) and \
        #         'Pat' in self.ptnmatcher(action_dict_step1.get(self.sentence_type), self.text) and\
        #         self.sentence_type == 'NONSCRIM':
        #     self.text = self.text
        #     self.processed_raw = self.beginning_context + ' ' + self.text
        #     self.named_line = 'pass '+self.named_line

        # for rushfumble with only fumle in the line:
        if re.search(r'fumbl', self.named_line) and self.sentence_type == 'SCRIM':
            self.text = re.sub(r'fumbl[sed]{1,2}', 'rush fumble', self.text)
            self.processed_raw = self.beginning_context + ' ' + self.text
            self.named_line = 'rush ' + self.named_line


    def deduct_passing_result(self):
        gain, loss = False, False
        text = self.text
        pass_but_no_result = 0
        pass_temps = sentence_pattern_model.get('actions').get('SCRIM').get('Pass')
        try:
            pass_temps.remove('back[sed]{0,2} to pass')
        except ValueError:
            pass
        pass_result_temps = sentence_pattern_model.get('results').get('Complete') + \
                            sentence_pattern_model.get('results').get('Incomplete') + \
                            sentence_pattern_model.get('results').get('Break_up') + \
                            sentence_pattern_model.get('results').get('Drop') + \
                            sentence_pattern_model.get('results').get('Sack') + \
                            sentence_pattern_model.get('results').get('Interception') + \
                            sentence_pattern_model.get('results').get('Touchdown') + \
                            [r'penal[izedty]{2,4}'] + \
                            sentence_pattern_model.get('results').get('First_down') + \
                            sentence_pattern_model.get('results').get('Safety')
        if any([bool(re.search(t, text)) for t in pass_temps]) and \
                not any([bool(re.search(t, text)) for t in pass_result_temps]):
            pass_but_no_result = 1
        if re.search(r'back[sed]{0,2} to pass', text):
            pass_but_no_result = 0
        if re.search(r'(?:gain|lose*s|lost)', text) and any([bool(re.search(t, text)) for t in pass_temps]):
            pass_but_no_result = 1
            gain = bool(re.search(r'gain', self.text))
            loss = bool(re.search(r'los[est]{0,2}', self.text))
        if self.sentence_type != 'SCRIM' or 'Interception' in self.ptnmatcher(result_dict, text):
            pass_but_no_result = 0

        if pass_but_no_result == 1:
            supv_ending_context = OneLine(self.game, self.index + 1).get_context()[0]
            i = self.index
            while supv_ending_context == "":
                i += 1
                try:
                    supv_ending_context = OneLine(self.game, i + 1).get_context()[0]
                except KeyError:
                    break
                except IndexError:
                    return self.text
            try:
                parsed_supv_context = self.parse_context(supv_ending_context)
            except TypeError:
                parsed_supv_context = None

            try:
                if parsed_supv_context and self.parsed_beginning_context[0] == self.parsed_beginning_context[3]:
                    if self.parsed_beginning_context[3] == parsed_supv_context[3]:
                        yds_diff = int(parsed_supv_context[4]) - int(self.parsed_beginning_context[4])
                        if yds_diff <= 0:
                            loss = True
                            gain = False
                        else:
                            loss = False
                            gain = True
                    else:
                        loss = False
                        gain = True
                if parsed_supv_context and self.parsed_beginning_context[0] != self.parsed_beginning_context[3]:
                    if self.parsed_beginning_context[3] == parsed_supv_context[3]:
                        yds_diff = int(parsed_supv_context[4]) - int(self.parsed_beginning_context[4])
                        if yds_diff >= 0:
                            loss = True
                            gain = False
                        else:
                            loss = False
                            gain = True
                    else:
                        loss = True
                        gain = False
            except ValueError:
                pass

        self.text += ' complete'*gain + ' incomplete'*loss
        # self.get_parentname()
        return pass_but_no_result, self.text


    def get_parentname(self):
        text = self.text
        sentence_type = self.sentence_type
        if sentence_type == 'META':
            major_ParentName = 'Meta'
            self.ParentName = 'Meta'
            return major_ParentName
        elif ',' in sentence_type and self.index > 12:
            major_ParentName = ''
            self.ParentName = 'OTHERTEXT'
            return major_ParentName

        # match for actions
        possible_actions = action_dict_step1.get(sentence_type)
        action_match_positions_start = {}
        action_match_positions_end = {}
        for k in possible_actions.keys():
            if any([bool(re.search(action_identifier, text)) for action_identifier in possible_actions.get(k)]):
                starting_position = min(
                    [re.search(action_temp, text).span()[0] for action_temp in possible_actions.get(k) if
                     bool(re.search(action_temp, text))])
                ending_position = max(
                    [re.search(action_temp, text).span()[1] for action_temp in possible_actions.get(k) if
                     bool(re.search(action_temp, text))])

                action_match_positions_start.update({k: starting_position})
                action_match_positions_end.update({k: ending_position})

        # if len(action_match_positions_start.keys()) == 0 and sentence_type == 'SCRIM':
        #     # nothing matched for a scrim, set default as RUSH. This is muted as per discussion 2019-10-05
        #     action_match_positions_start.update({'Rush': 0})

        # match for results
        result_match_positions_start = {}  # a dictionary of where each result match was found
        result_match_positions_end = {}
        for kkk in result_dict.keys():
            if any([bool(re.search(result_temp, text)) for result_temp in result_dict.get(kkk)]):
                starting_position = min(
                    [re.search(result_temp, text).span()[0] for result_temp in result_dict.get(kkk) if
                     bool(re.search(result_temp, text))])
                ending_position = max([re.search(result_temp, text).span()[1] for result_temp in result_dict.get(kkk) if
                                       bool(re.search(result_temp, text))])

                result_match_positions_start.update({kkk: starting_position})
                result_match_positions_end.update({kkk: ending_position})
        if len(
                result_match_positions_start) == 0:
            # so that simple rush and others with no obvious results can be matched
            result_match_positions_start.update({'': 3})

        self.anyactions = action_match_positions_start
        self.anyresults = result_match_positions_start
        # establish a distance matrix. SimpleRush are excluded because cannot get position for empty result.
        # But these two don't have continuations anyway, so no big problem.
        ParentNamesFound = {}
        for x in action_match_positions_start.keys():
            for y in result_match_positions_start.keys():
                for m in matching_tuple_dict.keys():
                    matching_tuple = matching_tuple_dict.get(m)
                    if x == matching_tuple[0] and y == matching_tuple[1]:
                        distance = result_match_positions_start.get(y) - action_match_positions_start.get(x)
                        ParentNamesFound.update({
                                                    m: (x, action_match_positions_start.get(x),
                                                        action_match_positions_end.get(x), y,
                                                        result_match_positions_start.get(y),
                                                        result_match_positions_end.get(y),
                                                        distance)})
                        # tuple structure:
                        # (ParentNameCandidate, action, where is the action (start, end),
                        # result, where is the result (start, end), distance between the starts
                        # the ParentName with smaller action_start will be used as the MajorParentName
                        # and check whether for MajorParentName continuation is allowed
        # print(ParentNamesFound)
        # 比赛开始
        arena = pd.DataFrame({
                                 'candidates': list(ParentNamesFound.keys()),
                                 'action': [ParentNamesFound.get(n)[0] for n in ParentNamesFound.keys()],
                                 'action_position_start': [ParentNamesFound.get(n)[1] for n in ParentNamesFound.keys()],
                                 'action_position_end': [ParentNamesFound.get(n)[2] for n in ParentNamesFound.keys()],
                                 'result': [ParentNamesFound.get(n)[3] for n in ParentNamesFound.keys()],
                                 'result_position_start': [ParentNamesFound.get(n)[4] for n in ParentNamesFound.keys()],
                                 'result_position_end': [ParentNamesFound.get(n)[5] for n in ParentNamesFound.keys()],
                                 'distance': [ParentNamesFound.get(n)[-1] for n in ParentNamesFound.keys()], })
        arena = arena.sort_values('distance', ascending=True)  # .drop_duplicates('action')
        arena = arena.sort_values('action_position_start').reset_index(drop=True)
        # print(arena)

        # continuation
        conti_actions = []
        conti_results = []
        major_ParentName = ''
        conti_flag = 0
        if len(ParentNamesFound) > 0:
            major_ParentName = arena.at[0, 'candidates']
            conti_flag = matching_tuple_dict.get(major_ParentName)[2]
            if conti_flag == 1:  # expecting continuation
                if arena.at[0, 'result_position_end']:
                    conti_start_pos = arena.at[0, 'result_position_end']
                else:
                    conti_start_pos = arena.at[0, 'action_position_end']
                conti_text = ' '.join(text[conti_start_pos:].split(' ')[1:])
                for k in possible_actions.keys():
                    if any([bool(re.search(action_identifier, conti_text)) for action_identifier in
                            possible_actions.get(k)]):
                        conti_actions.append(k)
                for kkk in result_dict.keys():
                    if any([bool(re.search(result_temp, conti_text)) for result_temp in result_dict.get(kkk)]):
                        conti_results.append(kkk)

        actions = ','.join(action_match_positions_start.keys())
        results = ','.join(result_match_positions_start.keys())

        # Hard Rules for special cases:
        if actions == 'Pat':
            if self.ptnmatcher(action_dict_step1.get('SCRIM'), text) == ['Pass']:
                major_ParentName = major_ParentName.replace('Kick', '2Pass')
                actions += ',Pass'
            elif self.ptnmatcher(action_dict_step1.get('SCRIM'), text) == ['Rush']:
                major_ParentName = major_ParentName.replace('Kick', '2Rush')
                actions += ',Rush'
        if 'Pass' in actions and 'loss' in text and not re.search(r'back to pass', self.text):
            rush_results = [matching_tuple_dict.get(k)[1] for k in matching_tuple_dict.keys() if 'Pass' in k]
            if not any([r in rush_results for r in results.split(",")]):
                results += ',Sack'
                major_ParentName = 'PassSack'
        if 'Rush' in actions and 'score' in text:
            results += 'Touchdown'
            major_ParentName = 'RushTD'
        if set(results.split(',')) == {'Touchdown', 'Complete'}:
            major_ParentName = [p for p in ParentNamesFound if 'TD' in p][0]
        if 'FieldGoal' in actions and 'Touchback' in results:
            major_ParentName = 'FGBad'
        if 'FieldGoal' in actions and results == "" and 'Penalty' not in actions:
            major_ParentName = 'FGGood'
        if actions == 'Rush':
            rush_results = ['Fumble', 'Touchdown', 'First_down', 'Safety', 'Timeout']
            if not any([r in rush_results for r in results.split(",")]):
                major_ParentName = 'RushSimple'
        if actions == 'Punt' and 'Dead' in results:  # Per BA
            major_ParentName = 'PuntDowned'
        if 'Punt' in actions and results == '':
            major_ParentName = 'PuntDowned'
        if actions in ['Pass', 'Rush'] and 'Touchdown' in results:
            major_ParentName = actions+'TD'
        if 'Pass' in actions and re.search(r'[in]*complete', text) and 'Touchdown' not in results:
            # Gives priority to 'incomplete/complete' as identifiers over 'long/short' as identifiers
            major_ParentName = 'Pass{}'.format(re.search(r'[in]*complete', text).group().title())
        if 'Sack' in results:
            major_ParentName = 'PassSack'
        if actions == "" and re.search(r'\bgain|loss\b', text):
            major_ParentName = 'RushSimple'

        self.ParentName = major_ParentName
        self.allow_continuation = conti_flag
        self.continuation_actions = conti_actions
        self.continuation_results = conti_results
        self.pn_arena = arena

        return major_ParentName, actions, results, conti_flag, conti_actions, conti_results


    def update_poss(self):
        if self.ParentName == 'Poss':
            self.poss = re.sub(r'[Pp]ossession:|[0-9]{1,2}:[0-9]{1,2}', '', self.text)
            self.poss = "".join([c for c in self.poss.strip() if c.isalpha()])
        elif self.beginning_context != "":
            self.poss = self.parsed_beginning_context[0]


    # def get_penalty_info(self):
    #     typeid = penalty_dict.get('PenaltyTypeId')
    #     outcomes = penalty_dict.get('Outcome')
    #     identified_pen_type, identified_outcomes, inplay = [], [], []
    #
    #     if any([re.search(temp, self.text) for temp in [r'pen\.', r'penal[izedty]{2,4}', r'illegal', r'ill.+prod']]):
    #         pen_flag = 'y'
    #         # search the penalty dictionary to match for the penalty type
    #         for k in typeid.keys():
    #             if any([bool(re.search(p, self.text)) for p in typeid.get(k).get('identifier')]):
    #                 identified_pen_type.append(k)
    #                 inplay.append(typeid.get(k).get('inplay'))
    #         for kk in outcomes.keys():
    #             if any([bool(re.search(pp, self.text)) for pp in outcomes.get(kk)]):
    #                 identified_outcomes.append(kk)
    #         self.penalty_info = ', '.join(['penalty: {}'.format(pen_flag),
    #                                        'type: {}'.format(','.join(identified_pen_type)),
    #                                        'outcome: {}'.format(','.join(identified_outcomes)),
    #                                        'inplay: {}'.format(','.join(inplay))])
    #     return self.penalty_info


    def review_all_attributes(self):
        return self.__dict__

#
# if __name__ == "__main__":
#     g = OneGame('alabama', 'ole miss', 1970)
#     g.process_one_line(239)
