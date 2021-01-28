import json
from datetime import datetime
import os

try:
    os.mkdir('Data Models')
except FileExistsError:
    pass

sentence_pattern_model = {
    'actions': {
        'GAMEHEADER': {
            'GameType': [r'bowl'],
            'TeamName': [r'\bvs\b', r'\bvs\.', r'\bversus\b', r'\buniversity\b'],
            'GameDate': [r'\bjanuary\b', r'\bjan\b', r'\bfebruary\b', r'\bfeb\b', r'\bmarch\b', r'\bmar\b', r'\bapril\b', r'\bapr\b',
                         r'\bmay\b', r'\bmay\b', r'\bjune\b', r'\bjun\b', r'\bjuly\b', r'\bjul\b', r'\baugust\b', r'\baug\b', r'\bseptember\b',
                         r'\bsep\b', r'\boctober\b', r'\boct\b', r'\bnovember\b', r'\bnov\b', r'\bdecember\b', r'\bdec\b', r'\bmonday\b',
                         r'\btuesday\b', r'\bwednesday\b', r'\bthursday\b', r'\bfriday\b', r'\bsaturday\b', r'\bsunday\b'],
            'Location': [r'stadium'],
            'Captains': [r'\bcaptains*\b'],
            'Attendance': [r'attendance'],
            'Weather': [r'weather', r'\bwind\b', r'temperature', r'overcast', r'sunny', r'clear', r'humid',
                        r'cloudy', r'windy', r'\btemp\b', r'\bgust\b', r'\bgusts\b', r'\bmph\b', r'degrees', r'degree',
                        r'\brain\b', r'shower', r'\bdry\b'],
            'GameKickoffTime': [r'kickoff.+[0-9]{1,2}:[0-9]{1,2}'],
            'Toss': [r'toss', 'coin toss', r'elect[sed]{0,2} to', r'defer[rsed]{0,3} choices',
                     r'elect[sed]{0,2} to (?:receive|defend)',r'will receive',r'defend (?:south|north|east|west) goal']
        },

        'GAMESTATUS': {
            'Poss': [r'[Pp]ossession:', r'\bball\b'],
            'PageNo': [r'page', r'\bpg\b'],
            'Score': [r'scor[eing]{1,3}', r'\btd\b', r'\bfg\b'],
            'GameClock': [r'[0-9]{0,2}:[0-9]{2,2}'],
            'Period': [r'\bhalf\b', r'[1-4] quarter', r'\bperiod\b'],
            'GameEnd': [r'end of game']
        },

        'OTHERTEXT': {
            'OtherText': [r'a^']
        },

        'SCRIM': {
            'Punt': [r'punt[sed]{0,2}'],
            'Rush': [r'\bstraight\b',
                     r'\bahead\b', r'\b[^hand off] up\b', r'\b[^hand off] middle\b',
                     r'\bcarry\b', r'\bisolation\b', r'\b(?<!wide) left|right\b',
                     r'\bcarrie[sd]{0,1}\b', r'\bcarried\b', r'\baround\b', r'\bdraw\b', r'\brun[sed]{0,2}\b',
                     r'\bran\b', r'\bburst[sed]{0,2}\b', r'\bcenter[seding]{0,3}\b'
                     r'\bsweep[sed]{0,2}\b', r'\bswept\b', r'\bisolate[sd]{0,1}\b',
                     r'\bsprint[sed]{0,2}\b', r'\bpitch[sed]{0,2}\b',
                     r'\b[^hand] off.+(?:left|right|lt|rt|tackle)\b',
                     r'\bover\b', r'\brush[sed]{0,2}\b', r'\bscrambl[seding]{0,3}\b', r'\bdelay-draw\b',
                     r'\brt\b', r'\blt\b', r'\bre\b', r'\ble\b', r'\brg\b', r'\blg\b', r'\bwent\b',
                     r'\breverse[sed]{0,2}\b', r'\btoss[sed]{0,2}\b', r'\bbootleg\b', r'\btrap[sed]{0,2}\b',
                     r'\binto center\b', r'\bhit the middle\b', r'\bright tackle\b', r'\bright end\b', r'\bsneak[sed]{0,2}\b',
                     r'\bkept\b', r'\bkeep[sed]{0,2}\b', r'\bslant[sed]{0,2}\b', r'\bisolate[sed]{0,2}\b',
                     r'\bleft tackle\b', r'\bright tackle\b', r'\bgo for\b', r'\bat center\b', r'\bforward\b', r'\boption[sed]{0,2}\b',
                     r'\bhand[sed]{0,2} [^off]\b', r'\bback[sed]{0,2} to pass\b', r'\bbobble[sed]{1,2}\b',
                     r'\bpitch-*out\b', r'\bpitch[sed]{0,2} out\b', r'\bhand-off\b', r'\bhand[sed]{0,2} *off\b',
                     r'\bsnap[speding]{0,4}\b'],

            'Pass': [r'\bpass[seding]{0,3}\b', r'\bpassing\b', r'\bhits*\b',
                     r'\bthrow[s]*\b', r'\bthrew\b', r'\bthrown\b',
                     r'\bscreen-pass[esd]{0,2}\b', r'\bscreen[sed]{1,2}\b',
                     r'\bfind[sed]{0,2}\b', r'\bgives*\b', r'\bgave\b',
                     r'\bback[sed]{0,2} to pass\b',
                     r'\broll[sed]{0,2} out\b', r'\bintend[sed]{1,2} for\b'],

            'PresnapPenalty': [r'\bpenal[izedty]{2,4}.*(?:off-*side|delay of game|false start)\b',
                               r'\b(?:off-*side|delay of game|false start|off *side).*penal[izedty]{2,4}\b',
                               r'\b(?:off-*side|delay of game|false start|off *side)\b',
                               r'\bholding penalty\b',
                               r'\b(?:for) delay\b',
                               r'\bdelay[sed]{0,2}\b',
                               r'\btoo much time\b',
                               r'\bpresnap\b'],

            'FieldGoal': [r'\bfg\b', r'\bfga\b', r'field goal', r'\bfgc\b', r'attempt[sed]{0,2}.*field goal']
            # WHEN KICK OFF COMES WITH POSSESSION / SPOT RAISE ALERT FOR BA. BUT FRANK WILL CREATE RULE JUST FOR KICKOFF
        },

        'NONSCRIM': {
            'Kickoff': [r'kick[sed]{0,2} *off', r'kicked-off', r'kick[sed]{0,2}'],
            'Pat': [r'\bpats*\b', r'points* after touchdown', r'pat kicks*', r'conver[tsedsion]{1,4}', r'kick attempt',
                    r'2-point conversion', r'2-pt conversion', r'extra point kick', r'extra point', r'\bxpa\b', r'2 points',
                    r'point after'],
            'Penalty': [r'\bpen\.*\b', r'penal[izedty]{2,4}', r'illegal[ly]{0,2}',  r'\bill\.*\b',
                        r'\bflag{1,2}[sed]{0,2}\b', r'\bfoul\b', r'\binterfer[enced]{0,4}\b', r'violation'],
            'Timeout': [r'time[sd]{0,1} *out'],
            'Dead': [r'dead *(?:ball)*', r'dead']
        }
    },
    # ----------------------------------------------------------

    'results': {
        'Return': [r'return[sed]{0,2}', r'\bret\.*\b', r'runs* back', r'ran back'],
        'Touchback': [r'touchback',
                      r'(?:in|into|to|through) (?:the)* *end *zone',
                      r'end zone',
                      r'(?:over|to) (?:the)* *goal line'],
        'Out_of_bounds': [r'out of bound[s]*', r'out-of-bounds', r'\boob\b'],
        'Fair_catch': [r'fair catch', r'\bfc\b'],
        'Downed': [r'[^1] down[sed]{0,2}\b', r'no run *back'],
        'Blocked': [r'block[sed]{0,2}'],
        'Fumble': [r'fumbl[sed]{0,2}', r'steal', r'stole'],  # r'fumbl[sed]{0,2}.+recover[sed]{0,2}', r'fumbl[sed]{0,2}.+lost',
        'Recovery': [r'recover[sed]{0,2}'],
        'Touchdown': [r'td', r'touch *down'],
        'First_down': [r'(?:1 *[st]{0,2}|first) down[sed]{0,2}'],
        'Safety': [r'saf[ety]{0,3}'],
        'Timeout': [r'time[sd]{0,1} *out'],
        'Complete': [r'[^un]success',
                     r'succeed[sed]{0,2}',
                     r'[^in]complete',
                     r'find',
                     # r'made',
                     r'scored',
                     r'\bgood\b',
                     r'pass.*caught'],
        'Incomplete': [r'fail[sed]{0,2}',
                       r'nogood',
                       r'no good',
                       r'\bbad\b',
                       r'unsuccessful',
                       r'incomplete', r'inc\.',
                       r'wide (?:to)* *(?:the)* *(?:left|right)*',
                       r'\b(?:too)* *(?:short|long)\b',
                       r'upright',
                       r'hit (?:left|right) upright',
                       r'hit cross *bar', r'hit the cross *bar',
                       r'overthrown',
                       r'bound[sed]{0,2} back',
                       'miss[sed]{1,2}'],
        'Break_up': [r'\bbrup\b', r'(?:broken*|breaks*) *up'],
        'Drop': [r'drop[peds]{1,3}'],
        'Sack': [r'sack[sed]{0,2}', r'for loss'],
                 # r'pass.*los[st]{1}'],
        'Interception': [r'intercept[ionsed]{0,3}', r'\bint\.*\b'],
        'On_side_kick': [r'on[ -]*side'],
        'Fake': [r'\bfake[sd]{0,1}\b'],
        'Dead': [r'dead *(?:ball)*', r'dead']
    }

}

now = str(datetime.now())

with open('Data Models/sentence_pattern_model.json', 'w') as file:
    json.dump(sentence_pattern_model, file)

print('loop 1 dictionary is updated on {}\n'.format(now))


# matching tuple for ParentName matching
matching_tuple_dict = {
    # dict of tuples: (action, result, continuation)
    # ----------- nonplays
    'GameType': ('GameType', '', 0),
    'TeamName': ('TeamName', '', 0),
    'GameDate': ('GameDate', '', 0),
    'Location': ('Location', '', 0),
    'Attendance': ('Attendance', '', 0),
    'Weather': ('Weather', '', 0),
    'GameKickoffTime': ('GameKickoffTime', '', 0),

    'Toss': ('Toss', '', 0),
    'Poss': ('Poss', '', 0),
    'PageNo': ('PageNo', '', 0),
    'Score': ('Score', '', 0),
    'GameClock': ('GameClock', '', 0),
    'Period': ('Period', '', 0),
    'OtherText': ('OtherText', '', 0),

    # ------------ scrims:
    # 'SimplePunt': ('Punt', '', 0),
    'PuntReturn': ('Punt', 'Return', 1),
    'PuntTB': ('Punt', 'Touchback', 0),
    'PuntOOB': ('Punt', 'Out_of_bounds', 0),
    'PuntFC': ('Punt', 'Fair_catch', 0),
    'PuntDowned': ('Punt', 'Downed', 0),
    'PuntFake': ('Punt', 'Fake', 1),
    'PuntBlocked': ('Punt', 'Blocked', 0),
    'PuntDead': ('Punt', 'Dead', 0),

    'RushSimple': ('Rush', '', 0),
    'RushFumble': ('Rush', 'Fumble', 1),
    'RushTD': ('Rush', 'Touchdown', 0),
    # 'RushDowned': ('Rush', 'Downed', 0),
    'RushFD': ('Rush', 'First_down', 0),
    'RushSAF': ('Rush', 'Safety', 0),
    'RushTimeout': ('Rush', 'Timeout', 0),

    'PassComplete': ('Pass', 'Complete', 0),
    'PassIncomplete': ('Pass', 'Incomplete', 0),
    'PassBrokenUp': ('Pass', 'Break_up', 0),
    'PassDrop': ('Pass', 'Drop', 0),
    'PassSack': ('Pass', 'Sack', 0),
    'PassInterception': ('Pass', 'Interception', 1),
    'PassTD': ('Pass', 'Touchdown', 0),
    'PassFD': ('Pass', 'First_down', 0),
    'PassSAF': ('Pass', 'Safety', 0),
    'PassTimeout': ('Pass', 'Timeout', 0),

    'PresnapPenalty': ('PresnapPenalty', '', 0),

    'FGGood': ('FieldGoal', 'Complete', 0),
    'FGBad': ('FieldGoal', 'Incomplete', 0),
    'FGFake': ('FieldGoal', 'Fake', 1),
    'FGBlock': ('FieldGoal', 'Blocked', 1),

    # ------------ nonscrims:
    'KickoffReturn': ('Kickoff', 'Return', 1),
    'KickoffTB': ('Kickoff', 'Touchback', 0),
    'KickoffOOB': ('Kickoff', 'Out_of_bounds', 0),
    'KickoffFC': ('Kickoff', 'Fair_catch', 0),
    'KickoffOnSideAttempt': ('Kickoff', 'On_side_kick', 1),

    'PATKickGood': ('Pat', 'Complete', 0),
    'PATKickBad': ('Pat', 'Incomplete', 0),
    'PATKickBlock': ('Pat', 'Blocked', 1),
    'PAT2RushGood': ('Pat', 'Complete', 0),
    'PAT2RushBad': ('Pat', 'Incomplete', 0),
    'PAT2RushFumble': ('Pat', 'Fumble', 1),
    'PAT2PassComplete': ('Pat', 'Complete', 0),
    'PAT2PassIncomplete': ('Pat', 'Incomplete', 0),
    'PAT2PassBrokenUp': ('Pat', 'Break_up', 0),
    'PAT2PassDrop': ('Pat', 'Drop', 0),
    'PAT2PassSack': ('Pat', 'Sack', 0),
    'PAT2PassInterception': ('Pat', 'Interception', 0),

    'Penalty': ('Penalty', '', 0),
    'TimeOut': ('Timeout', '', 0),
    'Dead': ('Dead', '', 0)
}

# output matching_tuple_dict to a json file
with open('Data Models/matching_tuple_dict.json', 'w') as j:
    json.dump(matching_tuple_dict, j)
print('matching_tuple is updated on {}\n'.format(str(datetime.now())))


# Numbers of ordinal numbers and cardinal numbers
numbers_dict = {'1': ['one', '1st', 'first'],
                '2': ['two', '2nd', 'second'],
                '3': ['three', '3rd', 'third'],
                '4': ['four', '4th', 'fourth'],
                '5': ['five', '5th', 'fifth'],
                '6': ['six', '6th', 'sixth'],
                '7': ['seven', '7th', 'seventh'],
                '8': ['eight', '8th', 'eighth'],
                '9': ['nine', '9th', 'ninth'],
                '10': ['ten', '10th', 'tenth'],
                '11': ['eleven', '11th', 'eleventh'],
                '12': ['twelve', '12th', 'twelfth'],
                '13': ['thirteen', '13th', 'thirteenth'],
                '14': ['fourteen', '14th', 'fourteenth'],
                '15': ['fifteen', '15th', 'fifteenth'],
                '16': ['sixteen', '16th', 'sixteenth'],
                '17': ['seventeen', '17th', 'seventeenth'],
                '18': ['eighteen', '18th', 'eighteenth'],
                '19': ['nineteen', '19th', 'nineteenth'],
                '20': ['twenty', '20th', 'twentieth'],
                '21': ['twenty-one', '21st', 'twenty-first'],
                '22': ['twenty-two', '22nd', 'twenty-second'],
                '23': ['twenty-three', '23rd', 'twenty-third'],
                '24': ['twenty-four', '24th', 'twenty-fourth'],
                '25': ['twenty-five', '25th', 'twenty-fifth'],
                '26': ['twenty-six', '26th', 'twenty-sixth'],
                '27': ['twenty-seven', '27th', 'twenty-seventh'],
                '28': ['twenty-eight', '28th', 'twenty-eighth'],
                '29': ['twenty-nine', '29th', 'twenty-ninth'],
                '30': ['thirty', '30th', 'thirtieth'],
                '31': ['thirty-one', '31st', 'thirty-first'],
                '32': ['thirty-two', '32nd', 'thirty-second'],
                '33': ['thirty-three', '33rd', 'thirty-third'],
                '34': ['thirty-four', '34th', 'thirty-fourth'],
                '35': ['thirty-five', '35th', 'thirty-fifth'],
                '36': ['thirty-six', '36th', 'thirty-sixth'],
                '37': ['thirty-seven', '37th', 'thirty-seventh'],
                '38': ['thirty-eight', '38th', 'thirty-eighth'],
                '39': ['thirty-nine', '39th', 'thirty-ninth'],
                '40': ['forty', '40th', 'fourtieth'],
                '41': ['forty-one', '41st', 'forty-first'],
                '42': ['forty-two', '42nd', 'forty-second'],
                '43': ['forty-three', '43rd', 'forty-third'],
                '44': ['forty-four', '44th', 'forty-fourth'],
                '45': ['forty-five', '45th', 'forty-fifth'],
                '46': ['forty-six', '46th', 'forty-sixth'],
                '47': ['forty-seven', '47th', 'forty-seventh'],
                '48': ['forty-eight', '48th', 'forty-eighth'],
                '49': ['forty-nine', '49th', 'forty-ninth'],
                '50': ['fifty', '50th', 'fiftieth'],
                '51': ['fifty-one', '51st', 'fifty-first'],
                '52': ['fifty-two', '51nd', 'fifty-second'],
                '53': ['fifty-three', '53rd', 'fifty-third'],
                '54': ['fifty-four', '54th', 'fifty-fourth'],
                '55': ['fifty-five', '55th', 'fifty-fifth'],
                '56': ['fifty-six', '56th', 'fifty-sixth'],
                '57': ['fifty-seven', '57th', 'fifty-seventh'],
                '58': ['fifty-eight', '58th', 'fifty-eighth'],
                '59': ['fifty-nine', '59th', 'fifty-ninth'],
                '60': ['sixty', '60th', 'sixtieth'],
                '61': ['sixty-one', '61st', 'sixty-first'],
                '62': ['sixty-two', '61nd', 'sixty-second'],
                '63': ['sixty-three', '63rd', 'sixty-third'],
                '64': ['sixty-four', '64th', 'sixty-fourth'],
                '65': ['sixty-five', '65th', 'sixty-fifth'],
                '66': ['sixty-six', '66th', 'sixty-sixth'],
                '67': ['sixty-seven', '67th', 'sixty-seventh'],
                '68': ['sixty-eight', '68th', 'sixty-eighth'],
                '69': ['sixty-nine', '69th', 'sixty-ninth'],
                '70': ['seventy', '70th', 'seventieth'],
                '71': ['seventy-one', '71st', 'seventy-first'],
                '72': ['seventy-two', '72nd', 'seventy-second'],
                '73': ['seventy-three', '73rd', 'seventy-third'],
                '74': ['seventy-four', '74th', 'seventy-fourth'],
                '75': ['seventy-five', '75th', 'seventy-fifth'],
                '76': ['seventy-six', '76th', 'seventy-sixth'],
                '77': ['seventy-seven', '77th', 'seventy-seventh'],
                '78': ['seventy-eight', '78th', 'seventy-eighth'],
                '79': ['seventy-nine', '79th', 'seventy-ninth'],
                '80': ['eighty', '80th', 'eightieth'],
                '81': ['eighty-one', '81st', 'eighty-first'],
                '82': ['eighty-two', '82nd', 'eighty-second'],
                '83': ['eighty-three', '83rd', 'eighty-third'],
                '84': ['eighty-four', '84th', 'eighty-fourth'],
                '85': ['eighty-five', '85th', 'eighty-fifth'],
                '86': ['eighty-six', '86th', 'eighty-sixth'],
                '87': ['eighty-seven', '87th', 'eighty-seventh'],
                '88': ['eighty-eight', '88th', 'eighty-eighth'],
                '89': ['eighty-nine', '89th', 'eighty-ninth'],
                '90': ['ninety', '90th', 'ninetieth'],
                '91': ['ninety-one', '91st', 'ninety-first'],
                '92': ['ninety-two', '92nd', 'ninety-second'],
                '93': ['ninety-three', '93rd', 'ninety-third'],
                '94': ['ninety-four', '94th', 'ninety-fourth'],
                '95': ['ninety-five', '95th', 'ninety-fifth'],
                '96': ['ninety-six', '96th', 'ninety-sixth'],
                '97': ['ninety-seven', '97th', 'ninety-seventh'],
                '98': ['ninety-eight', '98th', 'ninety-eighth'],
                '99': ['ninety-nine', '99th', 'ninety-ninth'],
                '100': ['one hundred', '100th', 'one hundredth']}
with open('Data Models/numbers.json', 'w') as j:
    json.dump(numbers_dict, j)


# stopwords for name searching 
name_stopwords = ['go', 'in', 'fc', 'at', 'fg', 'no', 'lg', 'to', 'up', 'td', 'lt', 'vs', 're', 'rt', 'pg', 'of', 'le',
                  'rg', 'the', 'nov', 'oct', 'ran', 'mar', 'fga', 'jan', 'oob', 'fgc', 'out', 'yds', 'too', 'apr',
                  'xpa', 'for', 'mph', 'use', 'hit', 'feb', 'off', 'sep', 'dec', 'jul', 'jun', 'may', 'bad', 'bar',
                  'end', 'aug', 'run', 'draw', 'temp', 'over', 'foul', 'page', 'june', 'vs\.', 'face', 'side', 'half',
                  'back', 'game', 'long', 'brup', 'some', 'went', 'good', 'wide', 'into', 'toss', 'pass', 'lost',
                  'yd\.*', 'wind', 'ball', 'made', 'mask', '2-pt', 'fair', 'line', 'zone', 'none', 'july', 'find',
                  'kick', 'kept', 'down', 'hand', 'time', 'coin', 'bowl', 'rain', 'goal', 'held', 'much', 'dead',
                  'left', 'hard', 'from', 'will', 'gust', 'int\.', 'delay', 'catch', 'extra', 'field', 'steal', 'april',
                  'point', 'sunny', 'ill\.', 'block', 'again', 'clear', 'pats*', 'guard', 'makes', 'false', 'stole',
                  'hands', 'swept', 'ahead', 'march', 'gusts', 'windy', 'carry', 'right', 'humid', 'cross[seding]{0,3}',
                  'shift', 'start', 'touch', 'short', 'inc\.*', 'threw', 'after', 'monday', 'nogood', '/bno/b',
                  'caught', 'friday', 'sunday', 'signal', 'degree', 'yards*', 'versus', 'scored', 'passer', 'bounds',
                  'kicks*', 'shower', 'runner', 'motion', 'tackle', 'helmet', 'cloudy', 'middle', 'center', 'around',
                  'period', 'thrown', 'holds*', 'august', 'ret\.*', 'upright', 'receive', 'pen[^n]', 'stadium',
                  'kicking', 'play[s]', 'tuesday', 'weather', 'carried', 'attempt', 'choices', '2-point', 'passing',
                  'bootleg', 'january', 'degrees', 'contact', 'helping', 'points*', 'october', 'presnap', 'illegal',
                  'forward', 'holding', 'defend', 'throwing', 'touching', 'on-*side', 'personal', 'hand-off',
                  'straight', 'los[set]', 'november', 'february', 'sideline', 'saturday', 'december', 'thursday',
                  'overcast', 'crossbar', 'grounding', 'interfere', 'throw[s]*', 'run *back', 'september', 'off-*side',
                  'wednesday', 'violation', 'bound[s]*', 'sidelines', 'equipment', 'isolation', 'procedure',
                  '[^no]good', 'touchback', 'downfield', 'touchdown', 'formation', 'possession', 'face *mask',
                  'infraction', 'per.* foul', 'pitch-*out', 'university', 'conversion', 'kicked-off', 'overthrown',
                  'noncontact', 'los[st]{1}', 'attendance', 'incomplete[sed]{0,2}', 'delay-draw', 'intentional',
                  'opportunity', 'ill.*proced', 'temperature', 'substitution', 'disqualified', 'unsuccessful',
                  'los[se]{1,3}', '(?:a|the|an)', '[^un]success', '[^in]complete[sed]{0,2}', 'out-of-bounds',
                  'fake[sd]{0,1}', '[1-4] quarter', 'saf[ety]{0,3}', 'run[sed]{0,2}', 'gain[sed]{0,2}',
                  'rush[sed]{0,2}', 'sack[sed]{0,2}', 'hold[sed]{0,2}', 'find[sed]{0,2}', 'fail[sed]{0,2}',
                  'roll[sed]{0,2}', 'hand[sed]{0,2}', 'keep[sed]{0,2}', 'pil[eing]{1,3}', 'trap[sed]{0,2}',
                  'toss[sed]{0,2}', 'punt[sed]{0,2}', 'kick[sed]{0,2}', 'down[sed]{0,2}', 'slant[sed]{0,2}',
                  'unsportsmanlike', 'elect[sed]{0,2}', 'refuse[sd]{0,1}', 'sneak[sed]{0,2}', 'burst[sed]{0,2}',
                  'delay[sed]{0,2}', 'bound[sed]{0,2}', 'carrie[sd]{0,1}', 'fumbl[sed]{0,2}', 'drop[peds]{1,3}',
                  'kick[sedr]{0,2}', 'catch[ing]{0,3}', 'scor[eing]{1,3}', 'sweep[sed]{0,2}', 'block[sed]{0,2}',
                  'pitch[sed]{0,2}', 'isolate[sd]{0,1}', 'option[sed]{0,2}', 'disqualification', 'screen[sed]{0,2}',
                  'decline[sd]{0,1}', 'sprint[sed]{0,2}', 'defer[rsed]{0,3}', 'return[sed]{0,2}', 'off side[sd]{0,2}',
                  'recover[sed]{0,2}', 'reverse[sed]{0,2}', 'receive[sed]{0,2}', 'isolate[sed]{0,2}',
                  'succeed[sed]{0,2}', 'kick[sed]{0,2}off', 'attempt[sed]{0,2}', 'rough[seding]{0,3}',
                  'clip[pingeds]{0,4}', 'scramble[sed]{0,2}', 'coach[seding]{0,3}', 'off-*side[sd]{0,2}',
                  'hold[rseding]{0,3}', 'time[sd]{0,1} *out', 'penal[izedty]{2,4}', 'strip[pseding]{0,4}',
                  'screen[sed]{0,2}dry', 'violat[sedion]{0,3}', '(?:broken*|breaks*)', 'interfer[enced]{0,4}',
                  'offset[stinged]{0,4}', 'pass[sed]{0,2}[^ing]', 'attempt[seding]{0,3}', '(?:try|tried|trying)',
                  'conver[tsedsion]{1,4}', 'screen-pass[esd]{0,2}', '[0-9]{0,2}:[0-9]{2,2}', 'intercept[ionsed]{0,3}',
                  'encroach[sedment]{0,4}', '(?:in|into|to|through)', 'back[sed]{0,2} to pass',
                  '(do|did|done|and|but|or)', '[0-9]{1,2} *[thrdstnd]{2}', '(?:participation|substitution)',
                  '(?:am|is|are|was|were|been|being)', '(?:on|over|accross|in|from|to|by|of|at|towards|against|for)',
                  'move[seding]{0,3}', 'deep', 'look[seding]{0,3}', 'tak[seding]{0,3}', 'took', 'cut[sing]{0,3}',
                  'leap[seding]{0,3}', 'get[sting]{0,4}', 'got', 'open[seding]{0,4}', 'too', 'back', 'low',
                  '[ap]\.*m\.*', 'stand[sing]{0,3}', 'stood', 'com[seing]{0,3}', 'came', 'dove', 't\.o\.',
                  '(?:their|our|him|his|her|it|them|us|me|you)', 'swing[seding]{0,3}', 'swang', 'swung',
                  '(?:have|having|has|had)', 'just', 'bama', 'as', 'total', 'f[ea]ll[sing]{0,3}', 'drive', 'he|she|us|']

with open('Data Models/football_name_stopwords.txt', 'w') as f:
    f.write('@'.join(name_stopwords))

