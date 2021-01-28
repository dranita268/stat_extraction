
from pymongo import MongoClient
from player_matching.team_master_provider import TeamMasterProvider
from player_matching.player_name_comparator import PlayerNameComparator

mongo_url = 'localhost:27017'
db_name = 'athlyte'
team_master_collection_name = 'TeamMaster'
active_rosters_collection_name = 'NewActiveRoster'  # 'NewActiveRoster_original'


class ActiveRoster(object):

    def __init__(self, player_name, pos, jersey_number, player_class, player_uuid, season):
        self.player_name = player_name
        self.pos = pos
        self.jersey_number = jersey_number
        self.player_class = player_class
        self.player_uuid = player_uuid
        self.season = season


class PlayerNameMatcher(object):

    def __init__(self, team_name, season, sport_code):
        self.team_name = team_name
        self.season = season
        self.sport_code = sport_code
        self.mongo_client = MongoClient(mongo_url)
        self.mongo_db = self.mongo_client[db_name]
        self.mongo_collection_ar = self.mongo_db[active_rosters_collection_name]
        self.players_dict = dict()
        self.player_name_comparator = PlayerNameComparator()


    def _get_team_code(self):
        team_master_prov = TeamMasterProvider(mongo_url, db_name, team_master_collection_name)
        return team_master_prov.get_team_data_from_master(self.team_name.strip(),
                                                          None, None)['teamCode']


    def _get_active_players(self, team_code, season, sport_code):

        prev_season_cnt = 0
        active_rosters_list = list()

        while prev_season_cnt < 4:
            active_rosters = self.mongo_collection_ar.find({'$and': [{'sportCode': sport_code}, {'season': season - prev_season_cnt},
                                                                     {'teamCode': team_code}]})
            active_rosters_list.append(active_rosters)
            prev_season_cnt += 1

        nxt_season_cnt = 0
        while nxt_season_cnt < 4:
            nxt_season_cnt += 1
            active_rosters = self.mongo_collection_ar.find({'$and': [{'sportCode': sport_code},
                                                                     {'season': season + nxt_season_cnt}, {'teamCode': team_code}]})
            active_rosters_list.append(active_rosters)

        active_rosters_dict = dict()

        for active_rosters in active_rosters_list:
            for active_roster in active_rosters:
                player_uuid = active_roster['playerId']
                player_pos = active_roster['position'] if 'position' in active_roster and active_roster['position'] is not None else 'NA'
                jersey_number = active_roster['jerseyNumber']
                player_class = active_roster['playerClass']
                player_name_arr = active_roster['playerName']
                season = active_roster['season']
                for player_name in player_name_arr:
                    roster = ActiveRoster(player_name, player_pos, jersey_number, player_class, player_uuid, season)
                    if player_name not in active_rosters_dict.keys():
                        active_rosters_dict[player_name] = roster
                player_name_alias_arr = active_roster['playerNameAlias'] if 'playerNameAlias' in active_roster else []
                for player_name_alias in player_name_alias_arr:
                    roster = ActiveRoster(player_name_arr[0], player_pos, jersey_number, player_class, player_uuid, season)
                    if player_name_alias not in active_rosters_dict.keys():
                        active_rosters_dict[player_name_alias] = roster

        return active_rosters_dict


    def find_match(self, player_name, position, category):

        if len(self.players_dict) == 0:
            team_code = self._get_team_code()
            self.players_dict = self._get_active_players(team_code, self.season, self.sport_code)

        found_player_name = self.player_name_comparator.compare_and_find_best_match(player_name, self.players_dict, category, position)

        # print ("\nMatched Player Name: " + str(found_player_name))
        return found_player_name


if __name__ == "__main__":
    matcher = PlayerNameMatcher('Alabama', 1972, 'MFB')
    matcher.find_match('DAVIS', '', '')
