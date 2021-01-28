import operator
from fuzzywuzzy import process
from fuzzywuzzy import fuzz
import re
from pyjarowinkler import distance
from metaphone import doublemetaphone

defense_positions = ['DB', 'DE', 'DL', 'DT', 'FS', 'LB', 'LCB', 'LDE', 'LDT', 'MLB', 'OLB', 'RCB', 'RDE', 'RDT', 'SLB', 'SS', 'WLB', 'TE', 'FL']
fg_positions = ['K', 'PK']
kickoff_returns_positions = ['KR', 'LCB', 'RB']
offense_positions = ['C', 'LG', 'LT', 'RG', 'RT', 'SN/C']
passing_positions = ['QB', 'FL']
punting_positions = ['P']
receiving_positions = ['FL', 'SE', 'SN/TE', 'TE', 'WR', 'RB', 'QB']
rush_positions = ['FB', 'RB', 'QB', 'WR']

positions_dict = dict()
positions_dict['rush'] = rush_positions
positions_dict['passing'] = passing_positions
positions_dict['receiving'] = receiving_positions
positions_dict['punting'] = punting_positions
positions_dict['punt'] = punting_positions
positions_dict['fg'] = fg_positions
positions_dict['punt returns'] = defense_positions
positions_dict['kickoff returns'] = kickoff_returns_positions
positions_dict['int returns'] = defense_positions
positions_dict['defense'] = defense_positions

FULL_100_PERCENT_MATCH = 100
NINTY_PERCENT_MATCH = 90
EIGHTY_PERCENT_MATCH = 80
SEVENTY_PERCENT_MATCH = 70
EIGHTY_FIVE_PERCENT_MATCH = 85

JW_ACCEPT_SCORE = 0.80
JW_NINTY_SCORE = 0.90


class PlayerNameComparator(object):

    def __init__(self):
        pass

    def compare_and_find_best_match(self, player_name, team_player_tag_objs, category, player_position):

        last_name = self._remove_start_end_commas(player_name.strip())

        jw_dist_dict = dict()
        for obj_player_name in team_player_tag_objs.keys():
            if len(obj_player_name.strip()) == 0:
                continue
            jw = distance.get_jaro_distance(last_name, obj_player_name, winkler=False, scaling=0.1)
            jw_dist_dict[obj_player_name] = jw

        sorted_jw_dist_dict = sorted(jw_dist_dict.items(), key = operator.itemgetter(1), reverse=True)
        if len(sorted_jw_dist_dict) > 0 and float(sorted_jw_dist_dict[0][1]) == 1.0:
            return sorted_jw_dist_dict[0][0]

        top_5_players = sorted_jw_dist_dict[:5]
        jw_list_above_75 = list()
        for top_5_player in top_5_players:
            if float(top_5_player[1]) > JW_NINTY_SCORE and self._compare_first_chars(last_name, top_5_player[0]):
                return top_5_player[0]
            if float(top_5_player[1]) >= JW_ACCEPT_SCORE and self._compare_first_chars(last_name, top_5_player[0]) and \
                    self._compare_player_context(category, team_player_tag_objs.get(top_5_player[0]), player_position):
                jw_list_above_75.append(top_5_player)

        if len(jw_list_above_75) == 1:
            return jw_list_above_75[0][0]

        matches_best = process.extractBests(last_name, team_player_tag_objs.keys(), limit=5)
        if len(matches_best) > 0 and int(matches_best[0][1]) == FULL_100_PERCENT_MATCH:
            return matches_best[0][0]

        mb_list_above_90 = list()
        for match_best in matches_best:
            if match_best[1] >= NINTY_PERCENT_MATCH and self._compare_first_chars(last_name, match_best[0]) and \
                    self._compare_player_context(category, team_player_tag_objs.get(match_best[0]), player_position):
                mb_list_above_90.append(match_best)

        if len(mb_list_above_90) == 1:
            return mb_list_above_90[0][0]
        else:
            set_ratio_100_percent_list = list()
            set_ratio_90_percent_list = list()
            for mb_player in matches_best:
                set_ratio = fuzz.token_set_ratio(last_name, mb_player[0])
                if set_ratio == FULL_100_PERCENT_MATCH:
                    set_ratio_100_percent_list.append(mb_player[0])

                if set_ratio >= EIGHTY_FIVE_PERCENT_MATCH and self._compare_first_chars(last_name, mb_player[0]):
                    matched_player = team_player_tag_objs.get(mb_player[0])
                    if matched_player.pos == 'NA' or player_position == 'NA' or matched_player.pos.lower() == player_position.lower() \
                        or self._is_positions_available_in_one_category(matched_player.pos, player_position):
                        set_ratio_90_percent_list.append(mb_player[0])

            if len(set_ratio_100_percent_list) == 1:
                return set_ratio_100_percent_list[0]
            elif len(set_ratio_100_percent_list) > 1:
                set_ratio_100_percent_context_list = list()
                for set_ratio_100_percent in set_ratio_100_percent_list:
                    matched_player = team_player_tag_objs.get(set_ratio_100_percent)
                    if self._compare_first_chars(last_name, set_ratio_100_percent) and \
                        (matched_player.pos == 'NA' or player_position == 'NA' or matched_player.pos.lower() == player_position.lower()
                         or self._is_positions_available_in_one_category(matched_player.pos, player_position)):
                        set_ratio_100_percent_context_list.append(set_ratio_100_percent)

                if len(set_ratio_100_percent_context_list) == 1:
                    return set_ratio_100_percent_context_list[0]

            if len(set_ratio_90_percent_list) > 0:
                return set_ratio_90_percent_list[0]

        double_metaphone_match = self._compare_double_metaphone(last_name, matches_best)
        if double_metaphone_match is not None:
            return double_metaphone_match

        match_one = process.extractOne(last_name, team_player_tag_objs.keys())
        if match_one is not None and match_one[1] >= NINTY_PERCENT_MATCH and self._compare_first_chars(last_name, match_one[0]):
            return match_one[0]

        # To handle 'Rahming, T.J.' and 'RAHMING,TJ', because first one is giving 3 token and second is returning 2 tokens,
        # after sorting order is getting disturbed.
        exact_match = self._compare_exact_text_match(last_name, match_one)
        if exact_match:
            return match_one[0]

        final_match = self._compare_final_match(last_name, matches_best)
        if final_match is not None:
            return final_match

        return None


    def _compare_double_metaphone(self, player_name, matches_best_five):
        player_name_tokens = self._get_token(player_name)

        if len(player_name_tokens) == 1:
            for matches_best in matches_best_five:
                compare_player_name_tokens = self._get_token(matches_best[0])
                for compare_player_name_token in compare_player_name_tokens:
                    compare_player_name_token_tuple = doublemetaphone(compare_player_name_token)
                    player_name_tokens_tuple = doublemetaphone(player_name_tokens[0])
                    if compare_player_name_token_tuple[0] == player_name_tokens_tuple[0] \
                            and self._compare_first_chars(player_name_tokens[0], compare_player_name_token) \
                            and matches_best[1] >= SEVENTY_PERCENT_MATCH:
                        return matches_best[0]
                    elif compare_player_name_token_tuple[1] == player_name_tokens_tuple[1] \
                            and self._compare_first_chars(player_name_tokens[0], compare_player_name_token) \
                            and matches_best[1] >= SEVENTY_PERCENT_MATCH:
                        return matches_best[0]

        return None


    def _compare_exact_text_match(self, player_name, matches_best_one):
        if matches_best_one is None:
            return False
        best_one = matches_best_one[0]
        regex = re.compile(r"[ ,.-]")
        return regex.sub('', player_name).lower() == regex.sub('', best_one).lower()


    def _compare_final_match(self, last_name, matches_best):

        if ',' not in last_name:
            return None
        fn = last_name[last_name.index(',') + 1:].strip()
        if len(fn) > 3:
            return None

        ln_ln = last_name[:last_name.index(',')].strip()

        for match in matches_best:
            if ',' not in match[0]:
                continue
            match_ln = match[0][:match[0].index(',')].strip()
            matched = match_ln.lower() == ln_ln.lower()

            if matched and self._compare_first_chars(last_name, match[0]):
                return match[0]

        return None


    def _compare_first_chars(self, player_name, compare_player_name):

        player_name_tokens = self._get_token(player_name)
        compare_player_name_tokens = self._get_token(compare_player_name)

        # only one name found in the input and compare player name. So Comparing first char always results to match.
        if len(player_name_tokens) == 1 and len(compare_player_name_tokens) == 1:
            if player_name.lower() in compare_player_name.lower():
                return True
            return player_name_tokens[0][:1].lower() == compare_player_name_tokens[0][:1].lower()

        # only one name found in the input. So Comparing first char always results to match.
        if len(player_name_tokens) == 1 and len(compare_player_name_tokens) > 1:
            if player_name.lower() in compare_player_name.lower():
                return True

            first_token_match = player_name_tokens[0][:1].lower() == compare_player_name_tokens[0][:1].lower()
            second_token_match = player_name_tokens[0][:1].lower() == compare_player_name_tokens[1][:1].lower()
            return first_token_match or second_token_match

        # only one name found in the compare name. So Comparing first char always results to match.
        if len(player_name_tokens) > 1 and len(compare_player_name_tokens) == 1:
            if player_name[0].lower() in compare_player_name.lower():
                return True

            first_token_match = player_name_tokens[0][:1].lower() == compare_player_name_tokens[0][:1].lower()
            second_token_match = player_name_tokens[1][:1].lower() == compare_player_name_tokens[0][:1].lower()
            return first_token_match or second_token_match

        first_token_match = player_name_tokens[0][:1].lower() == compare_player_name_tokens[0][:1].lower()
        second_token_match = player_name_tokens[1][:1].lower() == compare_player_name_tokens[1][:1].lower()
        third_token_match = True
        if len(player_name_tokens) == 3 and len(compare_player_name_tokens) == 3:
            third_token_match = player_name_tokens[2][:1].lower() == compare_player_name_tokens[2][:1].lower()

        # comparing player_name second token to compare_player_name third token.
        # Eg: Henry Ruggs to Henry Ruggs III. Sorted will be [Henry, Ruggs], [Henry, III, Ruggs]
        fourth_token_match = False
        if len(player_name_tokens) == 2 and len(compare_player_name_tokens) == 3:
            fourth_token_match = player_name_tokens[1][:1].lower() == compare_player_name_tokens[2][:1].lower()

        return first_token_match and (second_token_match or fourth_token_match) and third_token_match

    def _get_token(self, player_name):

        regex = re.compile(r"[ ,.-]")
        return sorted(regex.sub(' ', player_name).split())


    def _compare_player_context(self, player_category, player_tag_obj, player_position):

        if player_category is not None:
            positions_list = positions_dict.get(player_category.lower(), None)
            if positions_list is None:
                positions_list = offense_positions

            for position in positions_list:
                if position.lower() == player_tag_obj.pos.lower():
                    return True

            return False

        return player_position.lower() == player_tag_obj.pos.lower()


    def _is_positions_available_in_one_category(self, position1, position2):

        if position1 in defense_positions and position2 in defense_positions:
            return True

        return False

    def _remove_start_end_commas(self, player_name):

        cleaned_player_name = player_name
        if player_name.startswith(','):
            cleaned_player_name = player_name[1:]
        if player_name.endswith(','):
            cleaned_player_name = player_name[:len(player_name)-1]
        if player_name.startswith(',') and player_name.endswith(','):
            cleaned_player_name = player_name[:len(player_name) - 1]
            cleaned_player_name = cleaned_player_name[1:]

        return cleaned_player_name
