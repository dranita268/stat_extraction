import logging
from pymongo import MongoClient
import re
from bson.json_util import dumps


class TeamMasterProvider:

    def __init__(self, mongo_url='localhost:27017', mongo_db_name='athlyte', mongo_collection='TeamMaster'):
        self.logger = logging.getLogger(__name__)
        self.mongo_url = mongo_url
        self.mongo_db_name = mongo_db_name
        self.mongo_collection = mongo_collection
        self.mongo_client = MongoClient(self.mongo_url)
        self.mongo_db = self.mongo_client[self.mongo_db_name]
        self.mongo_connection = self.mongo_db[self.mongo_collection]

    def get_team_code_from_master(self, team):
        team_code = None
        team_name = self._trim_rank_string(team.attrib['name'])
        team_id = team.attrib['id']
        return self.get_team_data_from_master(team_name, team_id, team_code)["teamCode"]

    def get_teamdata_from_master(self, team):
        team_code = None
        team_name = self._trim_rank_string(team.attrib['name'])
        team_id = team.attrib['id']
        return self.get_team_data_from_master(team_name, team_id, team_code)

    def get_team_data_from_master(self, team_name, team_id, team_code):

        team_data = self.mongo_connection.find_one({"teamName": team_id})
        if team_data is not None:
            return team_data

        team_data = self.mongo_connection.find_one({"teamName": team_name})
        if team_data is not None:
            return team_data

        team_search = re.compile("^"+team_name+"$", re.IGNORECASE)
        if team_code is None or len(team_code) == 0:
            team_data = self.mongo_connection.find({"teamName": team_search})
        else:
            team_data = self.mongo_connection.find({"teamCode": team_code})

        name_team_list = self._get_team_list(team_data)
        if len(name_team_list) == 1:
            return name_team_list[0]
        elif len(name_team_list) > 1:
            self.logger.error("Multiple team found for " + team_name + ". got this dump " + dumps(name_team_list))

        modified_team_name = team_name.replace("State", "St.")
        modified_team_name = modified_team_name.replace(";", "")
        modified_team_search = re.compile("^"+modified_team_name+"$", re.IGNORECASE)

        team_data = self.mongo_connection.find({"teamName": modified_team_search})

        modified_team_list = self._get_team_list(team_data)
        if len(modified_team_list) == 1:
            return modified_team_list[0]
        elif len(modified_team_list) > 1:
            self.logger.error("Multiple team found for modified team name " + modified_team_name +
                              ". got this dump " + dumps(modified_team_list))

        team_data = self.mongo_connection.find({"teamNickNames": team_name})
        nickname_team_list = self._get_team_list(team_data)
        if len(nickname_team_list) == 1:
            return nickname_team_list[0]
        elif len(nickname_team_list) > 1:
            self.logger.error("Multiple team found for nickname direct search team name "
                              + str(nickname_team_list) + ". got this dump " + dumps(nickname_team_list))

        team_data = self.mongo_connection.find({"teamNickNames": team_search})
        nickname_team_list = self._get_team_list(team_data)
        if len(nickname_team_list) == 1:
            return nickname_team_list[0]
        elif len(nickname_team_list) > 1:
            self.logger.error("Multiple team found for nickname team name " + team_name
                              + ". got this dump " + dumps(nickname_team_list))

        raise ValueError("Team: <" + team_name + "> not found in team master")

    def _get_team_list(self, team_data):
        team_list = []
        for team in team_data:
            team_list.append(team)
        return team_list

    def _trim_rank_string(self, team_name):

        if team_name.startswith('#') or team_name.startswith('No.'):
            start_idx = 1 if team_name.startswith('#') else 2
            team_name_arr = team_name.split(' ')
            final_team_name = ''
            for i in range(start_idx, len(team_name_arr)):
                final_team_name += team_name_arr[i] + ' '
            return final_team_name.strip()

        return team_name.strip()

    '''def get_team_code_from_master(self, team_name, team_code):
        return self.get_team_data_from_master(team_name, None, team_code)['teamCode']
    '''

    def get_conference_details(self, team_code, season, sport_code):

        # print "TEAM " + team_code + " season " + str(season)
        pipeline = [
        {"$match": {"teamCode": team_code, "sportDetails.sportCode": sport_code,
            "sportDetails.confDetails.confStartYear": {"$lte": int(season)},
            "sportDetails.confDetails.confEndYear": {"$gte": int(season)},
            "sportDetails.confDetails.confDivisionStartYear": {"$lte": int(season)},
            "sportDetails.confDetails.confDivisionEndYear": {"$gte": int(season)} }},
         {"$unwind": "$sportDetails"},
         {"$unwind": "$sportDetails.confDetails"},
         {"$match": {"sportDetails.sportCode": sport_code, "sportDetails.confDetails.confStartYear": {"$lte": int(season)},
                     "sportDetails.confDetails.confEndYear": {"$gte": int(season)},
                     "sportDetails.confDetails.confDivisionStartYear": {"$lte": int(season)},
                     "sportDetails.confDetails.confDivisionEndYear": {"$gte": int(season)}}},
         {"$project": { "confName": "$sportDetails.confDetails.confName",
                     "confDivisionName" : "$sportDetails.confDetails.confDivisionName",
                     "confStartYear" : "$sportDetails.confDetails.confStartYear",
                     "confEndYear" : "$sportDetails.confDetails.confEndYear",
                     "confDivisionStartYear" : "$sportDetails.confDetails.confDivisionStartYear",
                     "confDivisionEndYear": "$sportDetails.confDetails.confDivisionEndYear"}}
        ]

        conf_details = self.mongo_connection.aggregate(pipeline)
        for data in conf_details:
            return data

        # print "Execute the 2nd pipeline for the conf process"
        pipeline2 = [
        {"$match": {"teamCode": str(team_code), "sportDetails.sportCode": sport_code,
            "sportDetails.confDetails.confStartYear": {"$lte": int(season)},
            "sportDetails.confDetails.confEndYear": {"$gte": int(season)}}},
         {"$unwind": "$sportDetails"},
         {"$unwind": "$sportDetails.confDetails"},
         {"$match": {"sportDetails.sportCode": sport_code, "sportDetails.confDetails.confStartYear": {"$lte": int(season)},
                     "sportDetails.confDetails.confEndYear": {"$gte": int(season)}}},
         {"$project": { "confName": "$sportDetails.confDetails.confName",
                     "confDivisionName" : "$sportDetails.confDetails.confDivisionName",
                     "confStartYear" : "$sportDetails.confDetails.confStartYear",
                     "confEndYear" : "$sportDetails.confDetails.confEndYear",
                     "confDivisionStartYear" : "$sportDetails.confDetails.confDivisionStartYear",
                     "confDivisionEndYear": "$sportDetails.confDetails.confDivisionEndYear"}}
        ]
        conf_details = self.mongo_connection.aggregate(pipeline2)
        for data in conf_details:
            # print "=================return the first "
            return data

        return None
