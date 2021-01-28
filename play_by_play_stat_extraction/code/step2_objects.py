import re
import pandas as pd
from datetime import datetime
import json
import xlsxwriter
import nameparser
from fuzzywuzzy import process
from nltk.tokenize import word_tokenize
import jellyfish
from tqdm import tqdm
import nltk
from copy import deepcopy
from player_matching.player_name_matcher import PlayerNameMatcher
import step1_objects
import xml_stat_validator as val
from PlayerRoleMapper import PlayerRoleMapper
from PenaltyParser import PenaltyParser
from KickPuntAnalyser import KickPuntAnalyser

context_regex_dict = step1_objects.context_regex_dict
# pk for a game: team1 - team2 - season  (multiple face-offs during the same season? )
# pk for a roster: team - season
# pk for a player: FullName-team-jersey no-season, but have unique id code given already

# load the data models required
with open('Data Models/football_name_stopwords.txt', 'r') as file:
    football_nonnames = [re.compile(r"\b{}\b".format(item)) for item in file.read().split('@')]
with open('Data Models/ParentName_role_model.json', 'r') as file:
    ParentName_role_model = json.loads(file.read())
with open('Data Models/matching_tuple_dict.json', 'r') as file:
    matching_tuple_dict = json.loads(file.read())
with open('Data Models/sentence_pattern_model.json', 'r') as j:
    sentence_pattern_model = json.loads(j.read())
with open('Data Models/loop_2_role_stats_model.json', 'r') as j:
    role_stats_model = json.loads(j.read())
with open('Data Models/loop_2_stat_templates_model.json', 'r') as j:
    stat_templates_model = json.loads(j.read())
with open('Data Models/ParentName_context_validation_model.json', 'r') as file:
    ParentName_context_validation = json.loads(file.read())
with open('Data Models/loop_2_empty_player_agg_stats.json', 'r') as file:
    empty_player_agg_stats = json.loads(file.read())
with open('Data Models/role_team_model.json', 'r') as file:
    role_team_model = json.loads(file.read())

action_dict = {}
action_dict.update(sentence_pattern_model.get('actions').get('SCRIM'))
action_dict.update(sentence_pattern_model.get('actions').get('NONSCRIM'))
result_dict = sentence_pattern_model.get('results')


'''
TwoGame: Game Object for Loop 2
'''


class TwoGame:  # pk for game and rosters to be further settled

    def __init__(self, h, v, year):
        self.path = 'loop1 output/' + ' '.join([h, "vs", v, str(year)]).title() + '.xlsx'
        self.game_df = pd.read_excel(self.path)
        self.v = v.lower()
        self.h = h.lower()
        self.year = str(year)
        self.team_abbreviations = self.initialize()
        self.h_abb, self.v_abb = self.match_team_with_abb()
        self.h_roster = self.get_roster(self.h)
        self.v_roster = self.get_roster(self.v)

        self.starting_possession = ""
        self.current_possession = ""

        # for score validation
        self.current_v_score = 0
        self.current_h_score = 0
        self.supv_current_v_score = 0
        self.supv_current_h_score = 0
        self.accumulated_score_deviation_v = 0
        self.accumulated_score_deviation_h = 0

        self.lines = []
        self.problem_lines = []  # lines that will stop the code from running. Not essentially the line wrongly parsed
        self.aggregated_players = None
        self.aggregated_teams = None
        self.play_by_play_stats = None
        self.offense_sheet = None
        self.defense_sheet = None
        self.spteam_sheet = None
        self.penalty_sheet = None
        self.BA_worksheet = None

        self.team_validation = None
        self.player_validation = None


    def __str__(self):
        return '_'.join([self.h, self.v, self.year])


    @staticmethod
    def parse_context(context):  # [POSS-DOWN-YTG-SPOTSIDE-SPOT]
        error = ''
        context = context.replace("goal", "g")
        if len(re.split(r'[ \t\-,/]', context)) < 4:
            poss_text, down_text, ytg_text, spotside_text, spotnum_text = '', '', '', '', ''
            error = 'context structure error'
            return poss_text, down_text, ytg_text, spotside_text, spotnum_text, error
        try:
            rest = context

            spot = re.search(r'(?:[A-Za-z]{1,3}[ \t\-\,/]*[0-9]{1,2}|50)$', context)
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

            down = re.search(r'[1234]', rest)
            down_text = down.group()

            ytg_text = rest[down.span()[1]:]

            poss_text = ''.join([t for t in poss_text if t.isdigit() or t.isalpha()])
            down_text = ''.join([t for t in down_text if t.isdigit() or t.isalpha()])
            ytg_text = ''.join([t for t in ytg_text if t.isdigit() or t.isalpha()])
            spotside_text = ''.join([t for t in spotside_text if t.isdigit() or t.isalpha()])
            spotnum_text = ''.join([t for t in spotnum_text if t.isdigit() or t.isalpha()])

        except AttributeError:
            poss_text, down_text, ytg_text, spotside_text, spotnum_text = '', '', '', '', ''
            error = 'context order error'
        return poss_text, down_text, ytg_text, spotside_text, spotnum_text, error


    def initialize(self):  # get team abbreviations
        self.game_df['context'] = self.game_df['context'].fillna("")
        contexts = self.game_df['context'].fillna("")
        self.game_df = self.game_df[['processed raw', 'context', 'poss', 'sentence_type', 'ParentName', 'dirty raw']]
        self.game_df.columns = ['processed raw', 'beginning context', 'poss', 'sentence_type', 'ParentName', 'dirty raw']
        team_abbreviations = list(set([self.parse_context(c)[0] for c in contexts if
                                       c != '' and self.parse_context(c)[-1] != 'context structure error']))
        team_abbreviations = [t for t in team_abbreviations if t != ""]
        return team_abbreviations


    def parse_game_header(self):  # get weather, toss, venue, attendance, captains, etc.
        header = self.game_df.loc[self.game_df['ParentName'] == 'Meta', 'raw']


    def match_team_with_abb(self):
        # Team 1: Alabama
        # Team 2: Auburn
        # Team 1: Letter or text used to identify field side "UA"
        # Team 2 : Letter or text used to identify field side "A"
        header = self.game_df.loc[self.game_df['processed raw'].str.contains('meta'), 'processed raw'].tolist()
        team1, team2 = [re.sub(r'team [12]: *|\(meta\)', '', h).strip() for h in header[:2]]
        team_abb_1, team_abb_2 = [re.sub(r'team [12]|:|team [12]:.+\(abbreviation used\)|\(meta\)|\"|letter or text used to identify field side',
                                         '', h.lower()).strip() for h in header[2:4]]

        match = process.extract(team1, [self.h, self.v])[0][0]
        if match == self.h:
            return [team_abb_1, team_abb_2]
        else:
            return [team_abb_2, team_abb_1]


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
                roster.at[i, 'Last'] = parsed_name.last
                # roster.at[i, 'Suffix'] = parsed_name.suffix

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
            roster = roster[
                ['Name', 'Last', 'Position', 'Jersey Number', 'Class', 'Player_id']]

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
        line = TwoLine(self, index)
        line.update_poss()
        line.update_quarter()
        line.get_score_supervision()
        line.first_penalty_parsing()

        if line.sentence_type in ['SCRIM', 'NONSCRIM']:
            line.find_names_from_raw()
            line.action_based_role_mapping()
            line.get_line_stats()
            if not pd.isna(line.ParentName):
                try:
                    line.modify_stats_for_punt_and_kickoff()
                    line.calculate_ending_context()
                    if line.penalty_info:
                        line.add_penalty_info_to_ending_context()
                    line.get_supv_ending_context()
                    if line.supv_ending_context != "":
                        line.context_validation()
                        line.context_validation_for_returns()
                except:
                    line.context_validation_alert = "can't calculate ending context, check typing issues"

        line.update_score()
        line.organize_stats()
        line.deduct_missing_score()
        line.manage_alerts()

        self.lines.append(line)
        return line


    def construct_play_by_play_stats(self):
        # df is the worksheet for BA to review. Construct the structure and multi-level index for the worksheet
        layer1, layer2 = [], []
        # empty_player_agg_stats.pop("tackle")
        for k in empty_player_agg_stats.keys():
            layer1 += [k] * len(empty_player_agg_stats.get(k).keys())
            layer2 += empty_player_agg_stats.get(k)
        arrays = [layer1, layer2]
        tuples = [('line', 'index'), ('line', 'sentence'), ('line', 'parentname'),
                  ('player', 'team'), ('player', 'name'), ('player', 'role')] + list(zip(*arrays))
        index = pd.MultiIndex.from_tuples(tuples)
        df = pd.DataFrame(columns=index)

        # write data extract results into the BA worksheet
        i = 0
        for l in self.lines:
            s = l.stats
            if s == {}:
                df.at[i, ('line', 'index')] = l.index
                df.at[i, ('line', 'sentence')] = l.raw
                df.at[i, ('line', 'parentname')] = l.ParentName
                i += 1
            else:
                for k in s.keys():
                    df.at[i, ('line', 'index')] = l.index
                    df.at[i, ('line', 'sentence')] = l.raw
                    df.at[i, ('line', 'parentname')] = l.ParentName
                    df.at[i, ('player', 'team')] = s.get(k).get('team')
                    df.at[i, ('player', 'role')] = s.get(k).get('role')
                    df.at[i, ('player', 'name')] = k
                    for col in df.columns[6:]:
                        df.at[i, col] = s.get(k).get(col[0]).get(col[1])
                    i += 1
        df = df.drop(columns='tackle', level=0)
        df = df.drop(columns='score', level=0)
        df = df.drop([('rush', 'yds'), ('receive', 'no')], axis=1)

        df.set_index([('line', 'index'), ('line', 'sentence'), ('line', 'parentname'), ('player', 'name')],
                     inplace=True, drop=True)

        self.play_by_play_stats = df
        return df


    @staticmethod
    def stats_add_stats(stats1, stats2):
        sum_stats = deepcopy(empty_player_agg_stats)
        for k in stats1.keys():
            for kk in stats1.get(k).keys():
                s1 = stats1.get(k).get(kk)
                s2 = stats2.get(k).get(kk)
                sum_stats.get(k).update({kk: s1+s2})
        return sum_stats


    def aggregate_player(self):  # distinguish 0 and null

        # output excel worksheet
        layer1, layer2, layer3 = [], [], []
        for k in empty_player_agg_stats.keys():
            layer1 += [k] * len(empty_player_agg_stats.get(k).keys())
            layer2 += ['Extracted']*len(empty_player_agg_stats.get(k).keys())
            layer3 += empty_player_agg_stats.get(k)
        arrays = [layer1, layer2, layer3]
        tuples = [('player', 'player', 'name'), ('player', 'player', 'team')] + list(zip(*arrays))
        index = pd.MultiIndex.from_tuples(tuples)
        df = pd.DataFrame(columns=index)
        df = df.drop(columns='tackle', level=0)
        df = df.drop(columns='score', level=0)
        df = df.drop([('rush', 'Extracted', 'yds'), ('receive', 'Extracted', 'no')], axis=1)

        i = 0
        valid = self.play_by_play_stats.loc[self.play_by_play_stats[('player', 'role')].notnull() &
                                            self.play_by_play_stats[('player', 'role')] != 'no role assigned', ]
        for team in [self.h_abb, self.v_abb]:
            d = valid.loc[valid[('player', 'team')] == team, ]
            for player_name in set(d.index.get_level_values(('player', 'name'))):
                # Found a new problem:
                # If a player name is not matched due to no roles assigned, the name will be dupliate for the same name
                # matched elsewhere. e.g. think of Cavan
                player_stats = d.loc[d.index.get_level_values(('player', 'name')) == player_name, ]
                df.at[i, ('player', 'player', 'name')] = player_name
                df.at[i, ('player', 'player', 'team')] = team
                for col in df.columns[2:]:
                    df.at[i, col] = sum(player_stats[(col[0], col[2])])
                i += 1

        df.set_index([('player', 'player', 'name'), ('player', 'player', 'team')], inplace=True, drop=True)
        self.aggregated_players = df
        # return df


    def aggregate_team(self):  # add up all players on each team into team stats
        layer1, layer2, layer3 = [], [], []
        for k in empty_player_agg_stats.keys():
            layer1 += [k] * len(empty_player_agg_stats.get(k).keys())
            layer2 += ['Extracted'] * len(empty_player_agg_stats.get(k).keys())
            layer3 += empty_player_agg_stats.get(k)
        arrays = [layer1, layer2, layer3]
        tuples = [('player', 'player', 'name'), ('player', 'player', 'team')] + list(zip(*arrays))
        index = pd.MultiIndex.from_tuples(tuples)
        df = pd.DataFrame(columns=index)
        df = df.drop(columns='tackle', level=0)
        df = df.drop(columns='score', level=0)
        df = df.drop([('rush', 'Extracted', 'yds'), ('receive', 'Extracted', 'no')], axis=1)

        i = 0
        for t in [self.h_abb, self.v_abb]:
            d = self.play_by_play_stats.loc[self.play_by_play_stats[('player', 'team')] == t, ]
            df.at[i, ('player', 'player', 'name')] = 'Team'
            df.at[i, ('player', 'player', 'team')] = t
            for col in df.columns[2:]:
                df.at[i, col] = sum(d[(col[0], col[2])])
            i += 1

        df.set_index([('player', 'player', 'name'), ('player', 'player', 'team')], inplace=True, drop=True)
        self.aggregated_teams = df
        # return df


    def obtain_xml_validation(self):
        try:
            validator = val.XMLValidator(self)
            cols_keep = [(c[0],"Reference",c[2]) for c in self.aggregated_players.columns]
            self.player_validation = validator.get_agg_player()[cols_keep]
            self.team_validation = validator.get_agg_team()[cols_keep]

            validation_df_p = self.aggregated_players.join(self.player_validation, how='outer').sort_index(axis=1)
            validation_df_t = self.aggregated_teams.join(self.team_validation, how='outer').sort_index(axis=1)
        except FileNotFoundError:  # if the test file has no XML ready
            validation_df_p = self.aggregated_players
            validation_df_t = self.aggregated_teams

        df = pd.concat([validation_df_p, validation_df_t], axis=0)
        # df = df.sort_index(level=1)
        df = pd.concat([df.loc[(df.index.get_level_values(0) != 'Team') & (df.index.get_level_values(1) == self.h_abb), ],
                        df.loc[(df.index.get_level_values(0) == 'Team') & (df.index.get_level_values(1) == self.h_abb), ],
                        df.loc[(df.index.get_level_values(0) != 'Team') & (df.index.get_level_values(1) == self.v_abb), ],
                        df.loc[(df.index.get_level_values(0) == 'Team') & (df.index.get_level_values(1) == self.v_abb), ]])
        offense = ['rush', 'pass', 'receive', 'fumble', 'conversions', 'misc']
        defense = ['defense', 'int', 'sack', 'brup']
        spteam = ['punt', 'pr', 'ko', 'kr', 'fga', 'patkick', 'patpass', 'patrush']

        # remove rows with all stats being zero
        self.offense_sheet = df[offense].loc[[index for index, row in df[offense].fillna(0).iterrows() if sum(row) > 0],]
        self.defense_sheet = df[defense].loc[[index for index, row in df[defense].fillna(0).iterrows() if sum(row) > 0],]
        self.spteam_sheet = df[spteam].loc[[index for index, row in df[spteam].fillna(0).iterrows() if sum(row) > 0],]



    def construct_penalty_sheet(self):
        layer1 = ['penalty info']*4
        layer2 = ['result', 'team', 'penalty yards', 'penalty alert']
        arrays = [layer1, layer2]
        tuples = [('line', 'index'), ('line', 'sentence'), ('penalty info', 'penalty type')] + list(zip(*arrays))
        index = pd.MultiIndex.from_tuples(tuples)
        pen_df = pd.DataFrame(columns=index)

        # write penalty info into the penalty worksheet
        i = 0
        for l in self.lines:
            pen = l.penalty_info
            if pen:
                for pen_type in pen.get('penalty info').keys():
                    pen_df.at[i, ('line', 'index')] = l.index
                    pen_df.at[i, ('line', 'sentence')] = l.raw
                    pen_df.at[i, ('penalty info', 'penalty type')] = pen_type
                    pen_df.at[i, ('penalty info', 'result')] = pen.get('penalty info').get(pen_type).get('result')
                    pen_df.at[i, ('penalty info', 'team')] = pen.get('penalty info').get(pen_type).get('team')
                    pen_df.at[i, ('penalty info', 'penalty yards')] = pen.get('penalty info').get(pen_type).get('yards')
                    if l.penalty_alert:
                        pen_df.at[i, ('penalty info', 'penalty alert')] = "; ".join(l.penalty_alert)
                    i += 1

        pen_df.set_index([('line', 'index'), ('line', 'sentence'),
                          ('penalty info', 'penalty alert'), ('penalty info', 'penalty type')],
                         inplace=True, drop=True)
        self.penalty_sheet = pen_df


    def output_backend_file(self):  # output a backend file with stats for trouble shooting
        output = pd.DataFrame()
        output['index'] = [l.index for l in self.lines]
        output['raw'] = [l.raw for l in self.lines]
        output['text'] = [l.text for l in self.lines]
        output['stats'] = [l.backend_stats for l in self.lines]
        output['possession'] = [l.poss for l in self.lines]
        output['ParentName'] = [l.ParentName for l in self.lines]

        output['beginning context'] = [l.beginning_context for l in self.lines]
        output['calculated ending context'] = [l.calculated_ending_context for l in self.lines]
        output['supervising ending context'] = [l.supv_ending_context for l in self.lines]
        output['context alert'] = [l.context_validation_alert for l in self.lines]

        output['{} score tracker'.format(self.h)] = [l.line_current_h_score for l in self.lines]
        output['{} score tracker'.format(self.v)] = [l.line_current_v_score for l in self.lines]
        output['{} score supv'.format(self.h)] = [l.line_supv_h_score for l in self.lines]
        output['{} score supv'.format(self.v)] = [l.line_supv_v_score for l in self.lines]
        output['missing score deduction'] = [l.missing_score_deduction for l in self.lines]

        df = output
        output_path = 'loop2 output/' + '/loop2_{}.xlsx'.format(' '.join([self.h, "vs", self.v, str(self.year)]).title())
        writer = pd.ExcelWriter(output_path, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='loop2', index=False)
        workbook = writer.book
        worksheet = writer.sheets['loop2']

        # auto fit col width
        def fit_width(col, hide=False, col_format={}):
            colname = df.columns[col]
            best_fit = max([len(str(x)) for x in df[colname].tolist() + [colname]])
            worksheet.set_column(first_col=col, last_col=col, width=best_fit, cell_format=col_format,
                                 options={'hidden': hide})

        # Default output has column names in bold. To remove the bold:
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, {})
        format2 = workbook.add_format()
        format2.set_align('left')
        format2.set_align('vjustify')
        format2.set_text_wrap()
        worksheet.set_column('B:D', width=40, cell_format=format2)
        writer.save()

    
    def construct_file_for_BA(self):
        ba_file_path = 'Loop2 BA Review/Round 7' + '/BA_Review {}.xlsx'.format(
            ' '.join([self.h, "vs", self.v, str(self.year)]).title())

        # drop some columns for BA's convenience
        def drop_some_cols(df):
            drop_cols = [('rush', 'att'), ('pass', 'att'), ('pass', 'sack'), ('pass', 'sackyds'),
                         ('int', 'no'), ('sack', 'no'),
                         ('punt', 'no'), ('pr', 'no'), ('ko', 'no'), ('kr', 'no'),
                         ('defense', 'fr'), ('fga', 'att'), ('patkick', 'att'), ('patrush', 'att'),
                         ('patpass', 'att'), ('conversions', 'thirdatt')]
            drop_cols_2 = [(c[0], 'Extracted', c[1]) for c in drop_cols]+[(c[0], 'Reference', c[1]) for c in drop_cols]
            for c in drop_cols+drop_cols_2:
                try:
                    df = df.drop(c, axis=1)
                except KeyError:
                    pass
            return df

        # the workbook has 5 worksheets, 4 of them need to drop some columns
        self.play_by_play_stats = drop_some_cols(self.play_by_play_stats)  # for BA review
        self.offense_sheet = drop_some_cols(self.offense_sheet)  # offense, defense, and spteams are for XML validation
        self.defense_sheet = drop_some_cols(self.defense_sheet)  # may have nothing if the game XML is not available
        self.spteam_sheet = drop_some_cols(self.spteam_sheet)

        # rename some columns
        def rename_some_cols(df):
            rename_cols = {'rush': 'Rush',
                           'fumble': 'Fumble',
                           'pass': 'Pass',
                           'receive': 'Reception',
                           'int': 'Interception',
                           'sack': 'Sack',
                           'brup': 'Brup',
                           'punt': 'Punt',
                           'pr': 'Punt Return',
                           'block': 'Block',
                           'ko': 'Kick Off',
                           'kr': 'Kick Return',
                           'defense': 'Defense',
                           'fga': 'Field Goal Attempt',
                           'patkick': 'PAT Kick',
                           'patrush': 'PAT Rush',
                           'patpass': 'PAT Pass',
                           'penalties': 'Penalties',
                           'conversions': 'Conversions',
                           'misc': 'Misc'}
            df = df.rename(columns=rename_cols, level=0)
            return df

        self.play_by_play_stats = rename_some_cols(self.play_by_play_stats)
        self.offense_sheet = rename_some_cols(self.offense_sheet)
        self.defense_sheet = rename_some_cols(self.defense_sheet)
        self.spteam_sheet = rename_some_cols(self.spteam_sheet)

        # get the columns to color in grey for BA's convenience
        def get_grey_cols(df):
            grey_formatting_columns = []
            try:
                m = len(df.index.levels)
            except AttributeError:
                m = 1
            for i in range(0, len(df.columns.get_level_values(0).unique())):
                isgrey = bool(i % 2)
                col = df.columns.get_level_values(0).unique()[i]
                for k in range(len(df[col].columns)):
                    # noinspection PyUnresolvedReferences
                    xlsx_col = xlsxwriter.utility.xl_col_to_name(m)
                    m += 1
                    grey_formatting_columns.append((xlsx_col, isgrey))
            return grey_formatting_columns

        s1_grey_cols = get_grey_cols(self.play_by_play_stats)
        s2_grey_cols = get_grey_cols(self.offense_sheet)
        s3_grey_cols = get_grey_cols(self.defense_sheet)
        s4_grey_cols = get_grey_cols(self.spteam_sheet)

        # get rows for team totals to be colored in green. Only for offense, defense, spteam sheets
        def get_team_rows(df):
            team_rows = []
            for i in range(len(df.index)):
                if df.index[i][0] == 'Team':
                    team_rows.append(i+4)
            return team_rows

        s2_team_rows = get_team_rows(self.offense_sheet)
        s3_team_rows = get_team_rows(self.defense_sheet)
        s4_team_rows = get_team_rows(self.spteam_sheet)

        # Remove the default pandas format for headers/index (bold, center).
        # This works for pandas 0.25, may change for future versions
        import pandas.io.formats.excel
        pandas.io.formats.excel.ExcelFormatter.header_style = None

        writer = pd.ExcelWriter(ba_file_path, engine='xlsxwriter')
        self.play_by_play_stats.to_excel(writer, sheet_name='Play by play stats')
        self.offense_sheet.to_excel(writer, sheet_name='Offense')
        self.defense_sheet.to_excel(writer, sheet_name='Defense')
        self.spteam_sheet.to_excel(writer, sheet_name='Special teams')
        self.penalty_sheet.to_excel(writer, sheet_name='Penalties')
        
        workbook = writer.book
        worksheet1 = writer.sheets['Play by play stats']
        worksheet2 = writer.sheets['Offense']
        worksheet3 = writer.sheets['Defense']
        worksheet4 = writer.sheets['Special teams']
        worksheet5 = writer.sheets['Penalties']

        # 5 useful formats
        format1 = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': 'black'})  # yellow back ground, for stats
        format2 = workbook.add_format()  # wrap text and center: for row indexes: sentence, parent, player name, etc
        format2.set_align('center')  # center alignment
        format2.set_text_wrap()  # wrap text
        format3 = workbook.add_format({'bg_color': '#90EE90', 'font_color': 'black',
                                       'top': 2, 'bottom': 2})  # light green
        # light grey background and all borders
        format4 = workbook.add_format({'bg_color': '#C0C0C0', 'border': 1})
        format5 = workbook.add_format()  # center, rotation
        format5.set_align('center')
        format5.set_rotation(90)

        # Xlsxwriter formatting functions
        def format_sheet1():  # play)by_play stats
            worksheet1.write('A3', 'i')
            worksheet1.write('B3', 'Sentence')
            worksheet1.write('C3', 'Parent')
            worksheet1.write('D3', 'Player')

            worksheet1.set_column('A:A', width=5)
            worksheet1.set_column('B:B', width=25, cell_format=format2)
            worksheet1.set_column("C:C", width=10, cell_format=format2)
            worksheet1.set_column("D:D", width=15, cell_format=format2)
            worksheet1.set_column("E:E", width=5)
            worksheet1.set_column("F:F", width=8, cell_format=format2)
            # For cells where stats were found and extracted, color it in yellow
            worksheet1.conditional_format('G4:DG1000',
                                         {'type':       'cell',
                                          'criteria':   '>',
                                          'value':       0,
                                          'format':     format1})
            worksheet1.set_row(0, height=65, cell_format=format5)
            worksheet1.set_row(1, height=65, cell_format=format5)
            # Grey background every other column per BA
            for col, isgrey in s1_grey_cols:
                if col != 'F':
                    worksheet1.set_column('{}:{}'.format(col, col), width=3)
                if isgrey:
                    worksheet1.set_column('{}:{}'.format(col, col), width=3, cell_format=format4)
                    worksheet1.conditional_format('{}1:{}2'.format(col, col), {
                        'type': 'cell', 'criteria': '!=', 'value': 0, 'format': format4})
            worksheet1.freeze_panes(3, 6)
            worksheet1.hide_zero()  # hide zeros for clearer look

        def format_sheet234(ws, grey_cols, team_rows):  # aggregated players stats
            ws.write('A4', 'Player Name')
            ws.write('B4', 'Team')
            ws.set_column('A:A', width=20, cell_format=format2)
            ws.set_column('B:B', width=10, cell_format=format2)
            ws.conditional_format('C4:DG1000',
                                          {'type': 'cell', 'criteria': '>', 'value': 0, 'format': format1})

            ws.set_row(0, height=65, cell_format=format5)
            ws.set_row(1, height=65, cell_format=format5)
            ws.set_row(2, height=65, cell_format=format5)
            for team_row in team_rows:
                ws.set_row(team_row, cell_format=format3)
            # Grey background every other column per BA
            for col, isgrey in grey_cols:
                ws.set_column('{}:{}'.format(col, col), width=3)
                if isgrey:
                    ws.set_column('{}:{}'.format(col, col), width=3, cell_format=format4)
                    ws.conditional_format('{}1:{}4'.format(col, col), {
                        'type': 'cell', 'criteria': '!=', 'value': 0, 'format': format4})
            ws.freeze_panes(4, 2)
            ws.hide_zero()  # hide zeros for clearer look

        format_sheet1()
        format_sheet234(worksheet2, s2_grey_cols, s2_team_rows)
        format_sheet234(worksheet3, s3_grey_cols, s3_team_rows)
        format_sheet234(worksheet4, s4_grey_cols, s4_team_rows)
        # format sheet 5
        worksheet5.write('A3', 'i')
        worksheet5.write('B3', 'Sentence')
        worksheet5.write('C3', 'Penalty alerts')
        worksheet5.write('D3', 'Penalty type')
        worksheet5.set_column('A:A', width=5)
        worksheet5.set_column('B:B', width=25, cell_format=format2)
        worksheet5.set_column("C:D", width=15, cell_format=format2)
        worksheet5.set_column('G:G', width=25, cell_format=format2)

        # add comments for sentences with alerts in worksheet 1
        worksheet1.set_comments_author('Validation Algorithm')
        for l in self.lines:
            if l.anyalert:
                # navigate to the row for the sentence with alert.
                l_row_num = sum([max(1, len(x.backend_stats.keys())) for x in self.lines if x.index < l.index])+4
                worksheet1.write_comment("B{}".format(l_row_num),
                                         l.alert_comment,
                                         {'x_scale': 2, 'y_scale': 1.5, 'font_size': 11})
                # print('alert for {} writen'.format(l.index))
        self.BA_worksheet = writer


    def extract_game_stats(self, save=True):
        print('Step 2', self)
        for i in tqdm(self.game_df.index):
            try:
                self.process_one_line(i)
            except:
                self.problem_lines.append(TwoLine(self, i))
                self.lines.append(TwoLine(self, i))  # make sure the output includes all lines, regardless of error

        self.output_backend_file()
        self.construct_play_by_play_stats()
        self.aggregate_player()
        self.aggregate_team()
        self.obtain_xml_validation()
        self.construct_penalty_sheet()
        self.construct_file_for_BA()
        if save:
            self.BA_worksheet.save()
        print("Extraction finished with {} problematic sentences".format(len(self.problem_lines)))


'''
-------------------------------------------------------------------------------------
TwoLine: Line Object for Loop 2
'''


class TwoLine:

    def __init__(self, TwoGame, ind):  # game is the game object
        self.index = ind
        self.game = TwoGame
        self.dirty_raw = TwoGame.game_df.at[ind, 'dirty raw']
        self.raw = TwoGame.game_df.at[ind, 'processed raw']

        self.beginning_context = TwoGame.game_df.at[ind, 'beginning context']
        self.parsed_beginning_context = self.game.parse_context(self.beginning_context)
        self.calculated_ending_context = None
        self.parsed_calc_ending_context = None
        self.supv_ending_context = None
        self.parsed_supv_context = None
        self.supv_line_index = None

        self.quarter = 0
        self.text = self.strip_context()
        self.standardized_text = self.text  # for action-based role mapping
        self.ParentName = TwoGame.game_df.at[ind, 'ParentName']
        self.sentence_type = TwoGame.game_df.at[ind, 'sentence_type']
        self.named_line = self.text
        self.tokens_possibly_names = None
        self.roled_line = self.text

        self.kopunt_analyser = None
        # self.penalty_parser = None
        self.penalty_info = None

        self.poss = ''
        self.backend_stats = {}  # unformatted stats, more convenient for line-level trouble shooting
        self.stats = {}  # formatted stats more consistent with XML structure and better for BA review/correction

        # for score validation
        self.line_current_h_score = self.game.current_h_score
        self.line_current_v_score = self.game.current_v_score
        self.line_supv_h_score = self.game.supv_current_h_score
        self.line_supv_v_score = self.game.supv_current_v_score
        self.score_deviation_h = 0
        self.score_deviation_v = 0
        self.missing_score_deduction = None

        self.anyalert = None
        self.context_alert = None
        self.penalty_alert = None
        self.context_validation_alert = None
        self.score_validation_alert = None
        self.position_validation_alert = None
        self.fg_pat_no_result = None
        self.alert_comment = None

    def __str__(self):
        return "\n".join([self.game.__str__(), str(self.index), self.raw])


    @staticmethod
    def parse_context(context):  # [POSS-DOWN-YTG-SPOTSIDE-SPOT]
        if context:
            context = context.replace("goal", "g")

        error = ''
        if len(re.split(r'[ \t\-,/]', context)) < 4:
            poss_text, down_text, ytg_text, spotside_text, spotnum_text = '', '', '', '', ''
            error = 'beginning context component missing'
            return poss_text, down_text, ytg_text, spotside_text, spotnum_text, error
        try:
            rest = context

            spot = re.search(r'(?:[A-Za-z]{1,3}[ \t\-\,/]*[0-9]{1,2}|50)$', context)
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

            down = re.search(r'[1234]', rest)
            down_text = down.group()

            ytg_text = rest[down.span()[1]:]

            poss_text = ''.join([t for t in poss_text if t.isdigit() or t.isalpha()])
            down_text = ''.join([t for t in down_text if t.isdigit() or t.isalpha()])
            ytg_text = ''.join([t for t in ytg_text if t.isdigit() or t.isalpha()])
            spotside_text = ''.join([t for t in spotside_text if t.isdigit() or t.isalpha()])
            spotnum_text = ''.join([t for t in spotnum_text if t.isdigit() or t.isalpha()])

        except AttributeError:
            poss_text, down_text, ytg_text, spotside_text, spotnum_text = '', '', '', '', ''
            error = 'context order error'

        return poss_text, down_text, ytg_text, spotside_text, spotnum_text, error


    def strip_context(self):
        if self.raw[0:15].count('/') >= 2:
            self.raw = self.raw.replace('/ ', '-').replace('/', '-')
        text = self.raw
        for key in context_regex_dict.keys():
            regex = context_regex_dict.get(key)
            context = re.search(regex, text)
            if context:
                text = re.sub(regex, '', text).strip().replace("-", " ")
                break
        # replace all whole school names into team abbreviations in case of 'Purdue 19' can't be recog. as ball spot
        text = re.sub(r'{}'.format(self.game.h) + r'( *[0-9]{1,2})', r'{}\1'.format(self.game.h_abb), text)
        text = re.sub(r'{}'.format(self.game.v) + r'( *[0-9]{1,2})', r'{}\1'.format(self.game.v_abb), text)

        return text


    def update_poss(self):
        if self.ParentName == 'Poss':
            self.poss = re.sub(r'[Pp]ossession:|[0-9]{1,2}:[0-9]{1,2}', "", self.raw).strip()
            self.poss = "".join([c for c in self.poss.strip() if c.isalpha()])
            self.game.current_possession = self.poss
        elif self.ParentName and self.beginning_context != "" and self.parsed_beginning_context[0] != "":
            self.poss = self.parsed_beginning_context[0]
            self.game.current_possession = self.poss
        else:
            self.poss = self.game.current_possession

        if self.poss == "" and not pd.isna(self.ParentName) and 'Kickoff' in self.ParentName:
            # Sometimes can't find direct poss for first kickoff of the game.
            # So need to infer from the following scrim play
            ind = self.index
            while TwoLine(self.game, ind).sentence_type != 'SCRIM':  # find the following scrim
                ind += 1
            original = TwoLine(self.game, ind).parsed_beginning_context[0]
            new = [x for x in self.game.team_abbreviations if x != original][0]
            self.poss = new
            self.game.current_possession = self.poss

        return self.game.current_possession


    def update_quarter(self):
        if self.sentence_type not in ['SCRIM', 'NONSCRIM'] and \
                re.search(r'[1-4] quarter|period', self.raw) and \
                'end' not in self.raw:
            self.quarter = re.search(r'\b[1-4]\b', self.raw).group()
        return self.quarter


    def first_penalty_parsing(self):
        penalty_parser = PenaltyParser(self)
        self.penalty_info = penalty_parser.gather_penalty_info()
        # remove the penalty part of the line in stat extraction.
        if self.penalty_info:
            self.text = self.text[:penalty_parser.penalty_start]
            self.penalty_alert = penalty_parser.penalty_alert


    def find_names_from_raw(self):
        roster = pd.concat([self.game.v_roster, self.game.h_roster])
        self.named_line = self.text
        text = re.sub(r'\b{}|{}\b'.format(self.game.h, self.game.v), "", self.text)
        for s in football_nonnames:
            text = re.sub(s, '', text)
            text = re.sub(r'\b(?:{}|{}\b)'.format(self.game.h_abb, self.game.v_abb)+' *[0-9]{1,2}', "", text)
            text = re.sub(r'[0-9]', '', text).strip()
        for s in football_nonnames:
            # a second time removing stopwords in case of any left-behinds due to order in the list
            text = re.sub(s, '', text)

        tokens = [t for t in word_tokenize(text) if
                  t.replace("'", "").replace(".","").isalpha() and
                  len(t.replace("'", "").replace(".","")) >= min([len(last) for last in roster['Last']])]
        tokens = list(set(tokens))
        self.tokens_possibly_names = {}

        for t in tokens:
            possible = process.extract(t, roster['Last'])[0:2]  # the top 2 most possible names
            self.tokens_possibly_names.update({t: [possible,
                                                   [x for x in nltk.word_tokenize(self.dirty_raw) if t.lower() in x.lower()][0]]})
            if possible[0][1] == 100:
                self.named_line = re.sub(r"\b{}\b".format(t.strip(".")), '<name {}>'.format(t), self.named_line)
            elif t.lower() in self.text and \
                    [x for x in nltk.word_tokenize(self.dirty_raw) if t.lower() in x.lower()][0].istitle():
                # the word should be capitalized in the original sentence to be considered a name
                self.named_line = re.sub(r"\b{}\b".format(t.strip(".")), '<name {}>'.format(t), self.named_line)
            elif possible[0][1] >= 85 and jellyfish.jaro_winkler(t, possible[0][0].lower()) > 0.8:
                # t should at least have a spelling similarity of 75 to be considered as a name
                self.named_line = re.sub(r"\b{}\b".format(t.strip(".")), '<name {}>'.format(t), self.named_line)

        # if not enough number of names were found with good enough matches on the roster, and if exactly the right
        # number of words were left after anti-joining the football nonnames, then just use the words left.
        role_dict = ParentName_role_model.get(self.ParentName)
        # if in the original un-lowercased raw sentence a token was not a NNP, then exclude it from being a name
        for t in tokens:
            if nltk.pos_tag([process.extract(t, nltk.word_tokenize(self.dirty_raw))[0][0]])[0][1] != 'NNP':
                tokens = [x for x in tokens if x != t]
        try:
            expected_count_of_roles = len([k for k in role_dict.keys() if len(role_dict.get(k)) > 0])
        except AttributeError:
            expected_count_of_roles = 0
        if expected_count_of_roles == len(tokens) and \
                expected_count_of_roles > len(re.findall(r'<name .+?>', self.named_line)):
            self.named_line = self.text
            for t in tokens:
                self.named_line = re.sub(t, '<name {}>'.format(t), self.named_line)

        return self.named_line  # may still contain name spelling issues


    # ONLY AS Stand-by information in case. NOT RUN IN TwoGame.process_one_line()
    def parent_based_role_mapping(self):  # NO LONGER DEPENDED
        # due to risky assumptions made on fixed sequential order of names:
        # Assumption: Major-offender, assist-offender, defender are normally in such 1-2-3 order in a sentence.
        tagged_line_with_role = self.named_line
        alert = ''
        try:
            action, result, contiflag = matching_tuple_dict.get(self.ParentName)
        except TypeError:
            action, result, contiflag = None, None, None

        names = [n for n in re.finditer(r'<name .+?>', self.named_line)]
        moff = 'No Major Offender'
        asoff = 'No Assist Offender'
        deff = 'No defender'
        if len(names) == 0:
            alert = 'No names found in the original sentence.'

        else:
            names = sorted(names, key=lambda x: x.span()[0])
            moff = names[0]
            if action == 'Pass' and self.ParentName not in ['PassSack', 'PassInterception'] and len(names) > 1:
                asoff = names[1]

        try:
            deff = [n for n in names if n != moff and n != asoff][0]
        except IndexError:
            pass

        def_team = [t for t in self.game.team_abbreviations if t != self.poss][0]
        role1 = {'moff': moff, 'asoff': asoff, 'deff': deff}
        role_team_dict = {'moff': self.poss,  # offending roles from possessing team, defending roles from the other
                          'asoff': self.poss,
                          'deff': def_team}

        for k in role1.keys():  # tag the names with roles
            try:
                role = ''.join(ParentName_role_model.get(self.ParentName).get(k))
                role_team = role_team_dict.get(k)
                if role != "":
                    name_role_string = role1.get(k).group().replace('>', "; {}; {}>".format(role, role_team))
                else:
                    name_role_string = role1.get(k).group().replace('>', "; {}>".format('N/A'))
                tagged_line_with_role = tagged_line_with_role.replace(role1.get(k).group(), name_role_string)
            except AttributeError:
                pass
        if self.ParentName in ['PATKickGood', 'PAT2RushGood', 'PAT2PassComplete']:
            tagged_line_with_role += ' good'

        # get assisting tacklers for RushSimple / RushFD
        unroled_names = [un for un in re.finditer(r"<name.+?>", tagged_line_with_role) if
                         ';' not in un.group() or 'N/A' in un.group()]

        if self.ParentName in ['RushSimple', 'RushFD', 'PassComplete', 'PuntReturn'] and \
                len(unroled_names) <= 2 and \
                re.search(r'<name.+tackler.+?>', tagged_line_with_role):
            for un in unroled_names:
                if 0 < un.span()[0]-re.search(r'<name.+tackler.+?>', tagged_line_with_role).span()[1] < 8:
                    un_str = re.sub(r"<|>", "", un.group().split(";")[0])
                    assist_tack = "<{}; tackler; {}>".format(un_str, def_team)
                    tagged_line_with_role = tagged_line_with_role.replace(un.group(), assist_tack)

        # if have obvious tackle sign
        tackle_sign = re.search('t(?:ackled)* by', tagged_line_with_role)
        if bool(tackle_sign):
            tackle_part = tagged_line_with_role[tackle_sign.span()[1]:]
            unroled_names = [un for un in re.finditer(r"<name.+?>", tackle_part)]
            for un in unroled_names:
                un_str = re.sub(r"<|>", "", un.group().split(";")[0])
                assist_tack = "<{}; tackler; {}>".format(un_str, def_team)
                tagged_line_with_role = tagged_line_with_role.replace(un.group(), assist_tack)

        # if have obvious interception sign
        int_sign = re.search('int(?:ercepted)* by', tagged_line_with_role)
        if bool(int_sign):
            int_part = tagged_line_with_role[int_sign.span()[1]:]
            un = [un for un in re.finditer(r"<name.+?>", int_part) if un.group()][0]
            inter_name = re.sub(r"<|>", "", un.group().split(";")[0])
            intercepter = "<{}; intercepter; {}>".format(inter_name, def_team)
            tagged_line_with_role = tagged_line_with_role.replace(un.group(), intercepter)

        return tagged_line_with_role
        # <name PDF_Stats_Extraction, passer, poss_team> to <name Jerry, receiver, poss_team>
        # intercepted by <name Tom, intercepter, non_poss_team>


    def action_based_role_mapping(self):  # better approach. Use this
        mapper = PlayerRoleMapper(self.named_line)
        roled_line = mapper.assign_roles_to_names()
        self.standardized_text = mapper.cleaned_line

        # assign teams
        def_team = [t for t in self.game.team_abbreviations if t != self.poss][0]
        off_team = self.poss
        names = re.findall(r'<name .*?>', roled_line)
        for name in names:
            team = 'N/A'
            role = [re.sub(r"[<> ]", "", t) for t in name.split(";")][1]
            if role != 'N/A':
                category = role_team_model.get(role)
                if category == 'offense':
                    team = off_team
                elif category == 'defense':
                    team = def_team
                else:  # fumble recovered by which team
                    next_poss = TwoLine(self.game, self.index + 1).update_poss()
                    team = next_poss

            roled_line = roled_line.replace(name, name.replace(">","; {}>".format(team)))

        # consult parent-based role mapping if the first player han't got role or team mapped for it.
        names = re.findall(r'<name .*?>', roled_line)
        try:
            parent_based_roled_line = self.parent_based_role_mapping()
        except IndexError:
            parent_based_roled_line = self.named_line
        names_from_parent_based_roles = re.findall(r'<name .*?>', parent_based_roled_line)
        if len(names) > 0 and "N/A" in names[0] and names[0].split(';')[0][6:-1] == names_from_parent_based_roles[0].split(';')[0][6:-1]:
            roled_line = roled_line.replace(names[0], names_from_parent_based_roles[0])

        # match player names in the text with Active Roster
        names = [n for n in re.finditer(r"<name.+?>", roled_line)]
        for name in names:
            name_string = [x.strip() for x in name.group()[5: -1].split(";")][0]
            try:
                team = [x.strip() for x in name.group()[5: -1].split(";")][2]
            except IndexError:
                team = 'N/A'
            if team != 'N/A':
                if team == self.game.h_abb:
                    team_name = self.game.h
                else:
                    team_name = self.game.v

                matcher = PlayerNameMatcher(team_name.title(), int(self.game.year), 'MFB')
                name_match = matcher.find_match(name_string, "", "")
                # replace the raw name string with the matched name from roster
                if name_match is not None:
                    roled_line = re.sub(r"\b{}\b".format(name_string), name_match, roled_line)
        self.roled_line = roled_line

        # if only rusher and tackler exist in the play, and no parent name matched, given it RushSimple
        if re.search(r"<name.+?>", roled_line) and \
            set([n.group().split("; ")[1] for n in re.finditer(r"<name.+?>", roled_line)]) == {'rusher','tackler'}:
            self.ParentName = "RushSimple"
        return self.roled_line


    def get_line_stats(self):
        roled_line = self.roled_line
        names = [n for n in re.finditer(r"<name.+?>", self.roled_line)]
        stats = {}
        poss = self.poss
        next_poss = TwoLine(self.game, self.index+1).update_poss()

        def get_stats_for_one_role(name_string, role):
            # for　role-based stats:
            role_based_stats = role_stats_model.get(role).get("role_based")
            for rs in role_based_stats:
                stats.get(name_string).update({rs: 'True'})

            # for template-based stats: choose the nearest if multiple same-class stats exists (e.g. more than 1 yardage)
            temp_based_stats = role_stats_model.get(role).get('temp_based')
            for ts in temp_based_stats:
                # print(ts)
                exist = [re.search(t, roled_line) for t in stat_templates_model.get(ts)
                         if bool(re.search(t, roled_line)) == True]
                if ts == 'yds':  # code yards differently from others
                    exist = []
                    for t in stat_templates_model.get(ts):
                        if bool(re.search(t, roled_line)):
                            exist += [l for l in re.finditer(t, roled_line)]
                    if len(exist) > 0:
                        yd_string = sorted(exist, key=lambda x: abs(x.span()[0] - name.span()[0]))[0]
                        yd_num = re.search(r'[0-9]{1,2}', yd_string.group()).group()

                    else:
                        yd_num = '0'
                    stats.get(name_string).update({ts: yd_num})

                elif ts not in ['inside20', 'plus50', 'pts', 'fumblercov_team', 'fumblercov_opp']:
                    # for other categorical temp_based_stats
                    detection = any([bool(e) for e in exist])
                    stats.get(name_string).update({ts: str(detection)})

                elif ts == 'pts':  # pts calculated by the way of scoring
                    points = 0
                    score_rules = {
                        'td': 6, 'fga': 3, 'saf': 2, 'pat': 1, 'patkick': 1, 'patrush': 2, 'patpass': 2}
                    for k in ['td', 'saf']:
                        if stats.get(name_string).get(k) == 'True':
                            points = score_rules.get(k)
                    for k in ['patkick', 'patrush', 'patpass', 'fga', 'pat']:
                        if stats.get(name_string).get(k) == 'True' and stats.get(name_string).get('good') == 'True':
                            points = score_rules.get(k)

                    stats.get(name_string).update(
                        {ts: points})  # td = 6, fg good = 3, patk = 1, patr good = patp good = 2, safety = 2
                elif ts in ['fumblercov_team', 'fumblercov_opp']:  # fumble recoveries
                    if poss == next_poss:
                        stats.get(name_string).update({'fumblercov_team': 'True', 'fumblercov_opp': 'False'})
                    else:
                        stats.get(name_string).update({'fumblercov_team': 'False', 'fumblercov_opp': 'True'})
                else:  # for inside 20 and plus50: depends on the yds stat
                    yard_num = stats.get(name_string).get('yds')
                    stats.get(name_string).update({'plus50': bool(float(yard_num) > 50)})
                    stats.get(name_string).update({'inside20': 'False'})

        for name in names:
            name_string = [x.strip() for x in name.group()[5: -1].split(";")][0]
            stats.update({name_string: {}})
            try:
                roles = name.group().split(";")[1].strip().split('+')
            except IndexError:
                roles = ['N/A']
            for role in roles:
                try:
                    get_stats_for_one_role(name_string, role)
                except AttributeError:
                    stats.get(name_string).update({role: 'True'})

        # correct the tackle stats for assist tackles
        tacklers = [name for name in names if 'tackler' in name.group()]
        tacka_bool = bool(len(tacklers) > 1)
        for t in tacklers:
            name_string = [x.strip() for x in t.group()[5: -1].split(";")][0]
            stats.get(name_string).update({'tacka': tacka_bool, 'tackua': not tacka_bool})

        self.backend_stats = stats
        return stats


    def modify_stats_for_punt_and_kickoff(self):
        self.kopunt_analyser = KickPuntAnalyser(self)
        self.kopunt_analyser.separate_inplay_summary()
        self.kopunt_analyser.get_stats()

        for name in self.backend_stats.keys():
            player_stats = self.backend_stats.get(name)
            if 'punt' in player_stats.keys():
                player_stats.update({'yds': self.kopunt_analyser.punt_yds})
            elif 'ko' in player_stats.keys():
                player_stats.update({'yds': self.kopunt_analyser.kickoff_yds})
            elif 'return' in player_stats.keys():
                player_stats.update({'yds': self.kopunt_analyser.return_yds})

        return self.backend_stats


    def calculate_ending_context(self):

        # parse the beginning context first
        b_poss, b_down, b_ytg, b_side, b_spot, error = self.parsed_beginning_context
        if error != '':
            return error

        # initializing
        yards_delta = 0  # positive if gain, negative if loss
        side_switch = False

        # get how many yards changed during the play
        if any([self.backend_stats.get(name).get('gain') == 'True' for name in self.backend_stats.keys()]) or \
                any([self.backend_stats.get(name).get('complete') == 'True' for name in self.backend_stats.keys()]) or\
                self.ParentName == 'PuntDowned':
            yards_delta = int(self.backend_stats.get(list(self.backend_stats.keys())[0]).get('yds'))
        elif any([self.backend_stats.get(name).get('loss') == 'True' for name in self.backend_stats.keys()]) or\
                any([self.backend_stats.get(name).get('incomplete') == 'True' for name in self.backend_stats.keys()]) or\
                re.search(r'loss', self.raw) and \
                any([self.backend_stats.get(name).get('loss') for name in self.backend_stats.keys()]):
            yards_delta = 0 - int(self.backend_stats.get(list(self.backend_stats.keys())[0]).get('yds'))

        if self.ParentName in ['PuntReturn', 'KickoffReturn'] and len(self.backend_stats.keys()) == 2:
            # punt/kickoff yards - return yards
            yards_delta = int(self.backend_stats.get(list(self.backend_stats.keys())[0]).get('yds')) - \
                          int(self.backend_stats.get(list(self.backend_stats.keys())[1]).get('yds'))

        def team_switcher(change, teams, original):
            new = original
            if change:
                new = [i for i in teams if i != original][0]
            return new

        if self.ParentName in ['PuntFake', 'PuntBlocked', 'RushFumble', 'RushSAF', 'PassSAF',
                               # 'PresnapPenalty', 'Penalty',
                               'FGGood', 'FGBad', 'FGFake', 'FGBlock', 'KickoffOnSideAttempt',
                               'PATKickGood', 'PATKickBad', 'PATKickBlock', 'PAT2RushGood', 'PAT2RushBad',
                               'PAT2RushFumble', 'PAT2PassComplete', 'PAT2PassIncomplete', 'PAT2PassBrokenUp',
                               'PAT2PassDrop', 'PAT2PassSack', 'PAT2PassInterception', 'TimeOut',
                               'Dead']:  # ParentNames skipped for context validation
            self.calculated_ending_context = '{} skipped in context validation'.format(self.ParentName)
            return '{} skipped in context validation'.format(self.ParentName)

        elif self.ParentName in ['PresnapPenalty', 'Penalty']:
            e_context = self.beginning_context  # may cause e_context be referenced before assignment error
            self.calculated_ending_context = e_context
            self.parsed_calc_ending_context = self.parse_context(e_context)
            return e_context

        elif not pd.isna(self.ParentName):
            # poss
            poss_switch = ParentName_context_validation.get(self.ParentName).get('poss_change')
            e_poss = team_switcher(poss_switch, self.game.team_abbreviations, b_poss)

            # down
            down_change = ParentName_context_validation.get(self.ParentName).get('e_down')
            if down_change == '1':
                e_down = 1
            elif down_change == 'plus 1':
                e_down = str((int(b_down) + 1) % 4)
                if e_down == '0':
                    e_down = "4"
                if b_ytg != 'g' and yards_delta >= int(b_ytg):
                    e_down = 1  # if b_ytg == 'g':  #     e_down = 1
            elif down_change == 'no change':
                e_down = b_down

            # spot and side
            e_spot = ParentName_context_validation.get(self.ParentName).get('e_spot')
            if 'TD' in self.ParentName:
                e_spot = b_spot
            if e_spot == "xx":
                if b_poss == b_side:
                    e_spot = int(b_spot) + yards_delta
                else:
                    e_spot = int(b_spot) - yards_delta

                if e_spot > 50:
                    side_switch = True
                    e_spot = 100 - e_spot
            e_side = team_switcher(side_switch, self.game.team_abbreviations, b_side)
            if 'TB' in self.ParentName:
                e_side = team_switcher(True, self.game.team_abbreviations, self.poss)

            if b_side == "" and b_spot == "50":
                if any([self.backend_stats.get(k).get('gain') == 'True' for k in self.backend_stats.keys()]) or \
                        any([self.backend_stats.get(k).get('complete') == 'True' for k in self.backend_stats.keys()]):
                    e_side = team_switcher(True, self.game.team_abbreviations, b_poss)

            # ytg
            ytg_change = ParentName_context_validation.get(self.ParentName).get('e_ytg')
            if ytg_change == 10:
                e_ytg = 10
            elif ytg_change == 'xx':
                if b_ytg == 'g':
                    e_ytg = 'g'
                else:
                    e_ytg = int(b_ytg) - yards_delta  # ytg is a countdown. Gain in yards will decrease ytg
                    if e_ytg <= 0:
                        e_ytg = min([10, e_spot])  # if less than 10yds to td, then ytg is the yards left

            e_context = e_poss + ' ' + str(e_down) + '-' + str(e_ytg) + ' ' + e_side + ' ' + str(e_spot)
            parsed_e_context = self.parse_context(e_context)

             # store the calculation results
            self.calculated_ending_context = e_context
            self.parsed_calc_ending_context = parsed_e_context
            return e_context


    def add_penalty_info_to_ending_context(self):
        pcec = self.parsed_calc_ending_context
        def_team = [t for t in self.game.team_abbreviations if t != self.poss][0]
        off_team = self.poss
        for pt in self.penalty_info.get('penalty info').keys():
            one_penalty = self.penalty_info.get('penalty info').get(pt)
            result, pen_team, yards_delta, lom, down_change = one_penalty.values()

            if any([v == 'unsure' for v in one_penalty.values()]):
                # when the information from penalty parser is not complete or firm
                pcec = self.calculated_ending_context
                continue
            else:
                if result == 'valid':
                    if lom == 'los':  # penalty is calculated from line of scrimmage (los)
                        b_poss, b_down, b_ytg, b_side, b_spot, error = self.parsed_beginning_context
                    else:  # penalty is calculated from spot of foul (sof)
                        b_poss, b_down, b_ytg, b_side, b_spot, error = self.parsed_calc_ending_context

                    e_poss = b_poss
                    if pen_team == off_team:  # offense pen_team is penalized
                        e_down = b_down

                        if b_side == pen_team:
                            e_side = b_side
                            e_spot = int(b_spot) - yards_delta
                        else: # b_side == def_team:
                            e_side = b_side
                            e_spot = int(b_spot) + yards_delta
                            if e_spot > 50:
                                e_side = off_team
                                e_spot = 100 - e_spot
                        e_ytg = int(b_ytg) + int(yards_delta)
                        if e_ytg < 0:
                            e_ytg = min([10, e_spot])
                            e_down = 1

                    elif pen_team == def_team:
                        e_down = b_down
                        if b_side == pen_team:
                            e_side = b_side
                            e_spot = int(b_spot) - yards_delta
                        else:  # b_side == off_team:
                            e_side = b_side
                            e_spot = int(b_spot) + yards_delta
                            if e_spot > 50:
                                e_side = def_team
                                e_spot = 100 - e_spot
                        e_ytg = int(b_ytg) + int(yards_delta)
                        if e_ytg < 0:
                            e_ytg = min([10, e_spot])
                            e_down = 1

                    pcec = e_poss + ' ' + str(e_down) + '-' + str(e_ytg) + ' ' + e_side + ' ' + str(e_spot)
                    # pcec: penalty calculated ending context
        self.calculated_ending_context = pcec
        self.parsed_calc_ending_context = self.parse_context(pcec)
        return pcec


    def get_supv_ending_context(self):
        if bool(self.calculated_ending_context) and self.beginning_context != "":
            self.supv_ending_context = TwoLine(self.game, self.index + 1).beginning_context
            i = self.index
            while self.supv_ending_context == "":
                i += 1
                try:
                    self.supv_ending_context = TwoLine(self.game, i + 1).beginning_context
                except KeyError:
                    break
            if self.ParentName in ['RushTD','PassTD'] or re.search(r'\bt[ouch]{0,4}d[own]{0,3}\b',self.roled_line):
                self.supv_ending_context = self.poss+' '+str(1)+'-'+str('10')+' '+self.parsed_beginning_context[3]+' '+str(0)
        try:
            self.parsed_supv_context = self.parse_context(self.supv_ending_context)
            self.supv_line_index = i
        except TypeError:
            pass

        if self.ParentName == 'KickoffReturn':
            ind = self.index
            while TwoLine(self.game, ind).sentence_type != 'SCRIM' or TwoLine(self.game, ind).beginning_context == "":
                ind += 1
            self.supv_ending_context = TwoLine(self.game, ind).beginning_context
            try:
                self.parsed_supv_context = self.parse_context(self.supv_ending_context)
                self.supv_line_index = ind
            except TypeError:
                pass
        return self.supv_ending_context


    def context_validation(self):
        if self.parsed_calc_ending_context and \
                self.parsed_supv_context and \
                self.parsed_calc_ending_context[1:5] != self.parsed_supv_context[1:5]:
            if self.parsed_calc_ending_context[3:5] == self.parsed_supv_context[3:5] and self.parsed_supv_context[2] == 'g':
                pass
            if 'error' in self.parsed_supv_context[-1] or 'error' in self.parsed_beginning_context[-1]:
                self.context_alert = "context structure error in beginning / supervision context"
            elif self.parsed_calc_ending_context[3] == self.parsed_supv_context[3] and \
                    0 < abs(int(self.parsed_calc_ending_context[4]) - int(self.parsed_supv_context[4])) <= 1:
                # 1 yard different tolerance in spot
                self.context_validation_alert = 'difference is only 1 yd, maybe tolerable'
                pass

            else:  # a disagreement is spotted
                self.context_validation_alert = 'disagreeing context from validation'

                if self.penalty_info:
                    # if penalty parser's result doesn't pass context validation, raise alert for manual review
                    self.context_validation_alert = 'manual check for penalty'
                    return

                # Reverse Validation: correct the original line stats using context_supv
                if self.parsed_beginning_context[0] == self.parsed_beginning_context[3]:
                    if self.parsed_beginning_context[3] == self.parsed_supv_context[3]:
                        yds_diff = int(self.parsed_supv_context[4]) - int(self.parsed_beginning_context[4])
                        if yds_diff < 0:
                            loss = True
                            gain = False
                        else:
                            loss = False
                            gain = True
                    else:
                        loss = False
                        gain = True
                        yds_diff = 100 - (int(self.parsed_supv_context[4]) + int(self.parsed_beginning_context[4]))

                else:
                    if self.parsed_beginning_context[3] == self.parsed_supv_context[3]:
                        yds_diff = int(self.parsed_supv_context[4]) - int(self.parsed_beginning_context[4])
                        if yds_diff > 0:
                            loss = True
                            gain = False
                        else:
                            loss = False
                            gain = True
                    else:
                        loss = True
                        gain = False
                        yds_diff = 100 - (int(self.parsed_supv_context[4]) + int(self.parsed_beginning_context[4]))

                if self.ParentName[0:4] in ['Rush', 'Pass']:
                    for name in self.backend_stats.keys():
                        player_stats = self.backend_stats.get(name)
                        if 'gain' in player_stats.keys():  # For rushing plays
                            player_stats.update({'gain': str(gain)})
                            player_stats.update({'loss': str(loss)})
                            if re.search(r"\b{}\b".format(str(abs(yds_diff))), self.text):
                                player_stats.update({'yds': abs(yds_diff)})
                        if 'complete' in player_stats.keys():  # For passing plays
                            player_stats.update({'complete': str(gain)})
                            player_stats.update({'incomplete': str(loss)})
                            if re.search(r"\b{}\b".format(str(abs(yds_diff))), self.text):
                                player_stats.update({'yds': abs(yds_diff)})
                        if 'TD' in self.ParentName or re.search(r'\bt[ouch]{0,4}d[own]{0,3}\b', self.roled_line):
                            player_stats.update({'yds': abs(yds_diff)})
                if self.ParentName == 'PuntDowned':
                    for name in self.backend_stats.keys():
                        player_stats = self.backend_stats.get(name)
                        if 'punt' in self.backend_stats.get(name):
                            player_stats.update({'yds': abs(yds_diff)})

                self.calculated_ending_context = self.calculate_ending_context()  # re-run to test reverse validation
                if self.parsed_calc_ending_context != self.parsed_supv_context:
                    self.context_validation_alert = 'still have problem'
                else:
                    self.context_validation_alert = 'reverse validation successful'


    def context_validation_for_returns(self):
        self.kopunt_analyser.context_validation_for_return_plays(self.parsed_supv_context)
        for name in self.backend_stats.keys():
            player_stats = self.backend_stats.get(name)
            if 'punt' in player_stats.keys():
                player_stats.update({'yds': self.kopunt_analyser.punt_yds})
            elif 'ko' in player_stats.keys():
                player_stats.update({'yds': self.kopunt_analyser.kickoff_yds})
            elif 'return' in player_stats.keys():
                player_stats.update({'yds': self.kopunt_analyser.return_yds})
        if self.kopunt_analyser.alert:
            self.context_validation_alert = self.kopunt_analyser.alert
        return self.backend_stats


    def update_score(self):  # for calculated score tracking
        pts_delta = 0
        for name in self.backend_stats.keys():
            if self.backend_stats.get(name).get('pts'):
                pts_delta += self.backend_stats.get(name).get('pts')
                # print(self.text, pts_delta)
                break
        if self.poss == self.game.v_abb:
            self.game.current_v_score += pts_delta
            self.line_current_v_score += pts_delta
        elif self.poss == self.game.h_abb:
            self.game.current_h_score += pts_delta
            self.line_current_h_score += pts_delta

        return {
            self.game.h: self.game.current_h_score, self.game.v: self.game.current_v_score}


    def get_score_supervision(self):
        # A standard score sentence: 'Score p:10 ms:3'
        if self.ParentName == 'Score':
            scores = re.findall(r'[a-z]{1,2}: *[0-9]{1,2}', self.raw)
            for s in scores:
                team, pts = [x.strip() for x in s.split(":")]
                if self.game.v_abb == team:
                    self.game.supv_current_v_score = int(pts)
                elif self.game.h_abb == team:
                    self.game.supv_current_h_score = int(pts)
        self.line_supv_h_score = self.game.supv_current_h_score
        self.line_supv_v_score = self.game.supv_current_v_score
        # print(self.game.h, self.line_current_h_score, self.line_supv_h_score, self.game.accumulated_score_deviation_h)
        # print(self.game.h, self.line_current_v_score, self.line_supv_v_score, self.game.accumulated_score_deviation_v)
        # the score deviation from this line. Prepare for next step: missing scoring deduction
        self.score_deviation_h = -(
                    self.game.current_h_score - self.game.supv_current_h_score) - self.game.accumulated_score_deviation_h
        self.score_deviation_v = -(
                    self.game.current_v_score - self.game.supv_current_v_score) - self.game.accumulated_score_deviation_v

        # update the cumulated deviations
        if self.ParentName == 'Score':
            self.game.accumulated_score_deviation_h = -(self.game.current_h_score - self.game.supv_current_h_score)
            self.game.accumulated_score_deviation_v = -(self.game.current_v_score - self.game.supv_current_v_score)
        return {
            self.game.h: self.game.supv_current_h_score, self.game.v: self.game.supv_current_v_score}


    def deduct_missing_score(self):
        score_dev = 0
        error_team = ''
        if self.ParentName == 'Score':
            possi = {
                '1': 'patkick', '2': ['patpass', 'patrush', 'saf'], '3': 'FG', '6': 'TD', '9': 'FG + TD'}
            if self.score_deviation_h == 0:
                error_team = self.game.v_abb
                score_dev = self.score_deviation_v
            elif self.score_deviation_v == 0:
                error_team = self.game.h_abb
                score_dev = self.score_deviation_h
            if score_dev != 0:
                # print('score_dev: ',score_dev)
                self.score_validation_alert = "missing score detected"
                suggest = possi.get(str(score_dev))
                if score_dev == 2:
                    # find the last play (scrim/nonscrim) nearest
                    i = self.index - 1
                    while TwoLine(self.game, i).sentence_type not in ['SCRIM', 'NONSCRIM'] or \
                            pd.isna(TwoLine(self.game, i).ParentName):
                        i = i - 1
                    previous_play = TwoLine(self.game, i)
                    if 'TD' in previous_play.ParentName:
                        deduct_range = '. '.join([TwoLine(self.game, x).find_names_from_raw() for x in range(i + 1, self.index)])
                        # print(deduct_range)
                        if 'rush' in deduct_range:
                            suggest = 'patrush'
                        elif 'pass' in deduct_range or re.search(r'<name.+?>.+to <name.+?>', deduct_range):
                            suggest = 'patpass'
                        elif 'kick' in deduct_range:
                            suggest = '2-pt patkick'
                    else:
                        suggest = 'saf'
                elif score_dev == 8:
                    suggest = 'TD + pat 2-pt cvsn'
                elif score_dev == 7:
                    suggest = 'TD + patkick'
                # print(self.game.current_possession)
                try:
                    self.missing_score_deduction = error_team + ":" + suggest
                except TypeError:
                    self.missing_score_deduction = 'deduction cannot be performed, please review original line'
                    # print(self.game.current_possession)  # print(suggest)  # print(self.review_all_attributes())


    def organize_stats(self):  # re-format stats extracted into the stat template. Run after all validations
        stats = {}
        players = re.findall(r'<name .+?>', self.roled_line)
        for p in sorted(set(players), key=lambda x: players.index(x)):
            if 'N/A' not in p and len(p.split(';')) == 3:
                # name, role, team has to be all valid for stats to be mapped correctly to template
                name, role, team = [x.strip() for x in p[5: -1].split(";")]
                p_stats = self.backend_stats.get(name)

                if name not in stats.keys():
                    stats.update({name: deepcopy(empty_player_agg_stats)})
                for r in role.split('+'):
                    try:  # holder is not extracted for stats so skipped by try statement
                        stat_key = role_stats_model.get(r).get('stat key')
                    except AttributeError:
                        continue

                    if stat_key == 'return':
                        if 'kicker' in self.roled_line:
                            stat_key = 'kr'
                        elif 'punter' in self.roled_line:
                            stat_key = 'pr'
                    target = stats.get(name).get(stat_key)
                    if not target:
                        # when a player is not a returner but assigned as a returner. e.g. Ala Vs Auburn 1996 line 18
                        continue

                    for k in p_stats.keys():
                        k1 = k
                        if k == stat_key or k == "return":
                            k1 = list({'att', 'no'}.intersection(set(target.keys())))[0]
                        curr = target.get(k1)
                        if curr is not None:
                            if str(p_stats.get(k)).isdigit():
                                new = curr + int(p_stats.get(k))
                            else:
                                if str(p_stats.get(k)) == 'True':
                                    new = curr + 1
                                else:
                                    new = curr + 0
                            target.update({k1: new})
            else:
                name = p[5: -1].split(";")[0].strip()
                role = 'N/A'
                team = 'N/A'
                if name not in stats.keys():
                    stats.update({name: deepcopy(empty_player_agg_stats)})

            stats.get(name).update({'team': team, 'role': role})
            stats.get(name).get('defense').update({'tacka': stats.get(name).get('tackle').get('tacka'),
                                                   'tackua': stats.get(name).get('tackle').get('tackua')})

            # template updates after a round of BA review
            gain = stats.get(name).get('rush').get('gain')
            loss = stats.get(name).get('rush').get('loss')
            r_yards = stats.get(name).get('rush').get('yds')
            stats.get(name).get('rush').update({'gain': gain * r_yards,
                                                'loss': loss * r_yards})

            # Derived stats
            if role == 'punter':
                p_yards = stats.get(name).get('punt').get('yds')
                p_spot = 100 - (int(self.parsed_beginning_context[-2]) + p_yards)
                stats.get(name).get('punt').update({'plus50': int(p_yards > 50)})
                stats.get(name).get('punt').update({'inside20': int(p_spot < 20)})
                stats.get(name).get('punt').update({'inside10': int(p_spot < 10)})
            if role in ['rusher','passer']:
                gain_yds = stats.get(name).get('rush').get('gain') + \
                           stats.get(name).get('pass').get('complete')*stats.get(name).get('pass').get('yds')
                ytg = self.parsed_beginning_context[2]

                if ytg.isdigit() and int(gain_yds) > int(ytg):
                    stats.get(name).get(role[0:4]).update({'fd': 1})
        self.stats = stats
        return stats


    def fg_pat_no_result_alert(self):
        alert = 0
        if re.search('<action (?:FieldGoal|Pat)>', self.standardized_text):
            if len(re.findall(r'<action .+?>', self.standardized_text)) > 1:
                search_range = self.standardized_text[re.search(r'<action (?:FieldGoal|Pat)>',
                                                                self.standardized_text).span()[1]:]
            else:
                search_range = self.standardized_text
            if not re.search(r'<result [In]complete', search_range):
                alert = 1
        message = 'Missing result Field Goal or PAT'
        return message*alert


    def manage_alerts(self):
        self.fg_pat_no_result = self.fg_pat_no_result_alert()
        self.anyalert = any([self.context_alert,
                             self.context_validation_alert,
                             self.score_validation_alert,
                             self.position_validation_alert,
                             self.fg_pat_no_result])
        alert_dict = {'context alert': self.context_alert,
                      'context validation alert': self.context_validation_alert,
                      'score validation alert': self.missing_score_deduction,
                      'player pos alert': self.position_validation_alert,
                      'fg pat no result alert': self.fg_pat_no_result
        }
        self.alert_comment = "\n".join([k+": "+alert_dict.get(k) for k in alert_dict.keys() if alert_dict.get(k)])

        # 4 types of alerts in the utility:
        # - context alert
        # - parent name alert
        # - player matching alert
        # - validation alert


    def review_all_attributes(self):
        return self.__dict__


# runfile('/Users/frankliucx/Desktop/Work-life/Athlyte/Frank_Play-by-Play/PDF_Stats_Extraction/step1_objects.py',
#         wdir='/Users/frankliucx/Desktop/Work-life/Athlyte/Frank_Play-by-Play/PDF_Stats_Extraction')
# runfile('/Users/frankliucx/Desktop/Work-life/Athlyte/Frank_Play-by-Play/PDF_Stats_Extraction/step2_objects.py',
#         wdir='/Users/frankliucx/Desktop/Work-life/Athlyte/Frank_Play-by-Play/PDF_Stats_Extraction')

# ------------------------------------------------------------
# 1st round of testing: files used for algorithm development
# onegames = [OneGame('purdue', 'illinois', 1962),
#             OneGame('purdue', 'minnesota', 1963),
#             OneGame('purdue', 'washington', 1962),
#             OneGame('purdue', 'iowa', 1960),
#             OneGame('purdue', 'michigan state', 1965)]
# for onegame in onegames:
#     onegame.analyse_game()

# twogames = [TwoGame('purdue', 'illinois', 1962),
#             TwoGame('purdue', 'minnesota', 1963),
#             TwoGame('purdue', 'washington', 1962),
#             TwoGame('purdue', 'iowa', 1960),
#             TwoGame('purdue', 'michigan state', 1965)]
# for twogame in twogames:
#     twogame.extract_game_stats()

# ------------------------------------------------------------
# 2nd round of testing: output organizing, process testing, accuracy testing
# onegames = [OneGame('purdue', 'notre dame', 1988),
#             OneGame('purdue', 'michigan state', 1977),
#             OneGame('purdue', 'illinois', 1988),
#             OneGame('purdue', 'illinois', 1980),
#             OneGame('purdue', 'miami', 1965),
#             OneGame('purdue', 'michigan', 1985),
#             OneGame('purdue', 'michigan state', 1992),
#             OneGame('purdue', 'michigan', 1978),
#             OneGame('purdue', 'minnesota', 1989),
#             OneGame('purdue', 'wisconsin', 1994),
#             OneGame('alabama', 'cincinnati', 1990),
#             OneGame('alabama', 'mississippi', 1975),
#             OneGame('alabama', 'auburn', 1980)
#             ]
# for onegame in onegames:
#     onegame.analyse_game()

# twogames = [TwoGame('purdue', 'notre dame', 1988),
#             TwoGame('purdue', 'michigan state', 1977),
#             TwoGame('purdue', 'illinois', 1988),
#             TwoGame('purdue', 'illinois', 1980),
#             TwoGame('purdue', 'miami', 1965),
#             TwoGame('purdue', 'michigan', 1985),
#             TwoGame('purdue', 'michigan state', 1992),
#             TwoGame('purdue', 'michigan', 1978),
#             TwoGame('purdue', 'minnesota', 1989),
#             TwoGame('purdue', 'wisconsin', 1994),
#             # TwoGame('alabama', 'cincinnati', 1990),
#             TwoGame('alabama', 'mississippi', 1975),
#             TwoGame('alabama', 'auburn', 1980)
#             ]
# for twogame in twogames:
#     twogame.extract_game_stats()


# ------------------------------------------------------------
# 3rd round of testing: XML data validation
# onegames = [OneGame('Alabama','Kentucky',1972),
#             OneGame('Alabama','Lsu',1988),
#             OneGame('Alabama','South Carolina',1966),
#             OneGame('Alabama','South Carolina',1967),
#             OneGame('Alabama','Houston',1971),
#             OneGame('Alabama','Virginia Tech',1968),
#             OneGame('Alabama','Tennessee',1973),
#             OneGame('Alabama','Mississippi',1970),
#             OneGame('Alabama','Auburn',1966),
#             OneGame('Alabama','Auburn',1988),
#             OneGame('Alabama','Southern Mississippi',1971)]
# for onegame in onegames:
#     onegame.analyse_game()
#
# twogames = [TwoGame('Alabama','Kentucky',1972),
#             TwoGame('Alabama','Lsu',1988),
#             TwoGame('Alabama','South Carolina',1966),
#             TwoGame('Alabama','South Carolina',1967),
#             TwoGame('Alabama','Houston',1971),
#             TwoGame('Alabama','Virginia Tech',1968),
#             TwoGame('Alabama','Tennessee',1973),
#             TwoGame('Alabama','Mississippi',1970),
#             TwoGame('Alabama','Auburn',1966),
#             TwoGame('Alabama','Auburn',1988),
#             TwoGame('Alabama','Southern Mississippi',1971)]
# for twogame in twogames:
#     twogame.extract_game_stats()

# ------------------------------------------------------------
# 5th round of testing: BA template review
# onegames = [OneGame('Alabama','Ole Miss',1970),
#             OneGame('Alabama','Mississippi State',1998),
#             OneGame('Purdue','notre dame',1980),
#             OneGame('Purdue','Ohio State',1988),
#             OneGame('Alabama','Kentucky',1972)
#             ]
# for onegame in onegames:
#     onegame.analyse_game()

# twogames = [TwoGame('Alabama','Ole Miss',1970),
#             TwoGame('Alabama','Mississippi State',1998),
#             TwoGame('Purdue','notre dame',1980),
#             TwoGame('Purdue','Ohio State',1988),
#             TwoGame('Alabama','Kentucky',1972)]
# for twogame in twogames:
#     twogame.extract_game_stats()


# ------------------------------------------------------------
# 6th round of testing: BA template review
# onegames = [OneGame('Alabama','Ole Miss',1970),
#             OneGame('Alabama','Mississippi State',1998),
#             OneGame('Purdue','notre dame',1980),
#             OneGame('Purdue','Ohio State',1988),
#             OneGame('Alabama','Kentucky',1972),
#             OneGame('Alabama','Houston',1971),
#             OneGame('Alabama','Virginia Tech',1968)
#             ]
# for onegame in onegames:
#     onegame.analyse_game()
#
# twogames = [TwoGame('Alabama','Ole Miss',1970),
#             TwoGame('Alabama','Mississippi State',1998),
#             TwoGame('Purdue','notre dame',1980),
#             TwoGame('Purdue','Ohio State',1988),
#             TwoGame('Alabama','Kentucky',1972),
#             TwoGame('Alabama','Houston',1971),
#             TwoGame('Alabama','Virginia Tech',1968)]
# for twogame in twogames:
#     twogame.extract_game_stats()
