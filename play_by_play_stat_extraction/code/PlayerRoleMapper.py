import nltk
import re


# A keyword can be regarded as an action if player names can be associated to it
action_dict = {
    'Punt': [r'punt[sed]{0,2}'],
    'Rush': [r'\bstraight\b',
             r'\bahead\b', r'\b[^hand off] *up\b', r'\b[^hand off] middle\b', r'\bmiddle\b',
             r'\bcarry\b', r'\bisolation\b', r'\b(?<!wide) left|right\b',
             r'\bcarrie[sd]{0,1}\b', r'\bcarried\b', r'\baround\b', r'\bdraw\b', r'\brun[sed]{0,2}\b',
             r'\bran\b', r'\bburst[sed]{0,2}\b', r'\bcenter[seding]{0,3}\b',
             r'\bsweep[sed]{0,2}\b', r'\bswept\b', r'\bisolate[sd]{0,1}\b',
             r'\bsprint[sed]{0,2}\b', r'\bpitch[sed]{0,2}\b',
             r'\b[^hand] off.+(?:left|right|lt|rt|re|le)\b',
             r'\bover\b', r'\brush[sed]{0,2}\b', r'\bscrambl[seding]{0,3}\b', r'\bdelay-draw\b',
             r'\brt\b', r'\blt\b', r'\bre\b', r'\ble\b', r'\brg\b', r'\blg\b', r'\bwent\b',
             r'\breverse[sed]{0,2}\b', r'\btoss[sed]{0,2}\b', r'\bbootleg\b', r'\btrap[sed]{0,2}\b',
             r'\binto center\b', r'\bhit the middle\b', r'\bright tackle\b', r'\bright end\b', r'\bsneak[sed]{0,2}\b',
             r'\bkept\b', r'\bkeep[sed]{0,2}\b', r'\bslant[sed]{0,2}\b', r'\bisolate[sed]{0,2}\b',
             r'\bleft tackle\b', r'\bright tackle\b', r'\bgo for\b', r'\bat center\b', r'\bforward\b',
             r'\boption[sed]{0,2}\b',
             r'\bhand[sed]{0,2} [^off]\b', r'\bback[sed]{0,2} to pass\b', r'\bbobble[sed]{1,2}\b',
             r'\bpitch-*out\b', r'\bpitch[sed]{0,2} out\b', r'\bhand-off\b', r'\bhand[sed]{0,2} *off\b',
             r'\bsnap[speding]{0,4}\b'],

    'Pass': [r'\bpass[seding]{0,3}\b', r'\bpassing\b', r'\bhits*\b',
             r'\bthrow[s]*\b', r'\bthrew\b', r'\bthrown\b',
             r'\bscreen-pass[esd]{0,2}\b', r'\bscreen[sed]{1,2}\b',
             r'\bfind[sed]{0,2}\b', r'\bgives*\b', r'\bgave\b',
             r'\bback[sed]{0,2} to pass\b',
             r'\broll[sed]{0,2} out\b', r'\bintend[sed]{1,2}\b'],

    'FieldGoal': [r'\bfg\b', r'\bfga\b', r'field goal', r'\bfgc\b', r'attempt[sed]{0,2}.*field goal'],

    'Kickoff': [r'kick[sed]{0,2} *off', r'kicked-off', r'kick[sed]{0,2}'],
    'Pat': [r'kick[sed]+ *pats*', r'\bpats*\b', r'points* after touchdown', r'pat kicks*', r'conver[tsedsion]{1,4}',
            r'kick attempt',
            r'2-point conversion', r'2-pt conversion', r'extra point kick', r'extra point', r'xpa', r'2 points',
            r'point after'],
    'Blocked': [r'block[sed]{0,2}'],
    'Return': [r'return[sed]{0,2}', r'\bret\.*\b', r'runs* back', r'ran back', r'\bfield[seding]{0,3}\b'],

    'Recovery': [r'recover[sed]{0,2}'],
    'Break_up': [r'\bbrup\b', r'(?:broken*|breaks*) *up', r'broken'],

    'Sack': [r'sack[sed]{0,2}', r'for loss'],
    'Tackle': [r'\bt by\b', r'\btackl[seding]{0,3}\b', r'\bdefend[seding]{0,3}\b', r'\bcaught\b'],
    # r'pass.*los[st]{1}'],
    'Fake': [r'\bfake[sd]{0,1}\b'],
    'Interception': [r'intercept[ionsed]{0,3}', r'\bint\.*\b'],
    'Hold': [r'h[oe]ld[sing]{0,3}']
}

result_dict = {
    'Complete': [r'[^un]success', r'succeed[sed]{0,2}', r'[^in]complete', r'find',  # r'made',
                 r'scored', r'[^no]good', r'pass.*caught'],
    'Incomplete': [r'fail[sed]{0,2}', r'nogood', r'no good', r'\bbad\b', r'unsuccessful', r'incomplete', r'inc\.',
                   r'wide *(?:to)* *(?:the)* *(?:left|right)*', r'\b(?:too)* *(?:short|long)\b', r'upright',
                   r'hit (?:left|right) upright', r'hit cross *bar', r'hit the cross *bar', r'overthrown',
                   r'bound[sed]{0,2} back', 'miss[sed]{1,2}'],
    'Touchback': [r'touchback',
                  r'(?:in|into|to|through) (?:the)* *end *zone',
                  r'end zone',
                  r'(?:over|to) (?:the)* *goal line'],
    'Touchdown': [r'\btd\b', r'touch *down'],
    'Out_of_bounds': [r'out of bound[s]*', r'out-of-bounds', r'\boob\b'],
    'Fair_catch': [r'fair catch', r'\bfc\b'],
    'First_down': [r'(?:1 *[st]{0,2}|first) down[sed]{0,2}'],
    'On_side_kick': [r'on[ -]*side'],
    'Fumble': [r'fumbl[sed]{0,2}', r'steal', r'stole'],
    'Dead': [r'dead *(?:ball)*', r'dead'],
    'Drop': [r'drop[peds]{1,3}'],
    'Gain': [r'\bgain[seding]{0,3}\b'],
    'Loss': [r'\blos[sedingt]{1,3}\b']
}

yardage = [r'[0-9]{1,2} (?:yards*|yds*)',
           r'(?:gain[sed]{0,2}|lost|loss) [0-9]{1,2}',
           r'(?:for|of) [0-9]{1,2}']
spots = r'[a-z][0-9]{1,2}'


action_role_dict = {'Punt': 'punter',
                    'Rush': 'rusher',
                    'Pass': 'passer',
                    'FieldGoal': 'fgattempter',
                    'Kickoff': 'kicker',
                    'Pat': 'patattempter',
                    'Blocked': 'blocker',
                    'Return': 'returner',
                    'Recovery': 'recover',
                    'Break_up': 'breaker',
                    'Sack': 'sacker',
                    'Tackle': 'tackler',
                    'Fake': 'faker',
                    'Interception': 'intercepter',
                    'Hold': 'holder'}


class PlayerRoleMapper:

    def __init__(self, named_line):
        self.named_line = named_line
        self.standardized_line = ""
        self.tagged_line = ""
        self.cleaned_line = ""
        self.roled_line = ""


    def assign_roles_to_names(self):
        self._standardize()
        self._tag_pos()
        self._clean_up()
        self.roled_line = self._map_roles()
        self.roled_line = self.rewind_standardize()
        return self.roled_line


    def _standardize(self):  # a named line
        l = self.named_line
        chunks = re.split(r'(<name .*?>)', l)
        std_l = ""
        for chunk in chunks:
            if re.search(r'<name .*?>', chunk):
                std_l += chunk
            else:
                std_chunk = chunk
                for action in action_dict.keys():
                    patterns = action_dict.get(action)
                    for p in patterns:
                        if p == r'for loss' and 'pass' not in std_chunk.lower():
                            continue  # 'for loss' only map to sack in passing plays
                        std_chunk = re.sub(p, " {} ".format(action), std_chunk)

                for result in result_dict.keys():
                    patterns = result_dict.get(result)
                    for p in patterns:
                        std_chunk = re.sub(p, " {} ".format(result), std_chunk)
                std_l += std_chunk
        self.standardized_line = std_l
        return std_l


    def _tag_pos(self):  # a named line
        tag_l = self.standardized_line
        # names = re.findall(r'<name .+?>', l)
        rest = nltk.word_tokenize(re.sub(r'<name .+?>', "", tag_l))
        rest = list(set(rest))
        for token in rest:
            if token in action_dict.keys():
                if token == "Sack" and 'Pass' not in rest:
                    continue
                else:
                    tag_l = re.sub(token, '<action {}>'.format(token), tag_l)
            elif token in result_dict.keys():
                tag_l = re.sub(token, '<result {}>'.format(token), tag_l)
        self.tagged_line = tag_l
        return tag_l


    def _clean_up(self):  # a tagged line
        clean_l = self.tagged_line
        chunks = re.split(r"<name .*?>", clean_l)
        for chunk in chunks:
            actions_in_sentence = [x for x in re.finditer(r'<action .*?>', chunk)]
            for a in actions_in_sentence:
                if a.group() in chunk[:a.span()[0]]:  # if already seen such instance within the same chunk before
                    cleaned_chunk = chunk[:a.span()[0]] + " " + chunk[a.span()[1]:]
                    clean_l = clean_l.replace(chunk, cleaned_chunk)

            results_in_sentence = [x for x in re.finditer(r'<result .*?>', chunk)]
            for r in results_in_sentence:
                if r.group() in chunk[:r.span()[0]]:  # if already seen such instance within the same chunk before
                    cleaned_chunk = chunk[:r.span()[0]] + " " + chunk[r.span()[1]:]
                    clean_l = clean_l.replace(chunk, cleaned_chunk)
        self.cleaned_line = clean_l
        return clean_l


    @staticmethod
    def get_sentence_structure(cleaned_l):  # a cleaned line
        names = [x for x in re.finditer(r'<name .+?>', cleaned_l)]
        actions = [x for x in re.finditer(r'<action .+?>', cleaned_l)]
        results = [x for x in re.finditer(r'<result .+?>', cleaned_l)]
        return names, actions, results


    def _map_roles(self):  # a cleaned line
        # search for "by" closely behind the action, if found, use that name
        # if no "by" closely behind the action, use the closest name in front of it
        # if no unoccupied name in front of it, use the closest name behind it.
        # special function for tacklers, receivers, returners
        line = self.cleaned_line
        names, actions, results = self.get_sentence_structure(self.cleaned_line)
        # split the sentence by action keywords
        chunks = [c.strip() for c in re.split(r'(<action .*?>)', self.cleaned_line) if len(c.strip()) > 0]
        enumerated_tokens = [i for i in enumerate(chunks)]
        for a in actions:
            action = re.sub(r'<action |>', "", a.group())
            expected_role = action_role_dict.get(action)
            action_ind = [t for t in enumerated_tokens if t[1] == a.group()][0][0]
            chunk_before_action, chunk_after_action = "", ""
            if action_ind > 0:
                chunk_before_action = chunks[action_ind-1]
            try:
                chunk_after_action = chunks[action_ind+1]
            except IndexError:
                pass

            # for punter/kicker and returners
            kicker_to_returner_pattern = re.search('<name .*?>.+<action .*?> .*(?:to|downed by) [a-z]*\.* *<name .*?>', self.cleaned_line)
            # fielded by is one of the return identifiers so no need to include in the pattern above
            if action in ['Punt', 'Kickoff'] and kicker_to_returner_pattern:
                acter, returner = re.findall(r'<name .*?>', kicker_to_returner_pattern.group())[-2:]
                line = line.replace(acter, acter.replace(">", "; {}>".format(expected_role)))
                line = line.replace(returner, returner.replace(">", "; {}>".format('returner')))

            else:  # for other actions
                try:
                    # by + name after this action and before next action or no names before this action
                    if re.search(r'\bby *[a-z]*\.* *<name .*?>', chunk_after_action) or \
                            not re.search(r'<name .*?>', chunk_before_action):
                        name = re.search(r'<name .*?>', chunk_after_action)

                        if name:
                            target_name = re.findall(r'<name .*?>', chunk_after_action)[0]
                            line = line.replace(target_name,
                                                target_name.replace(">", "; {}>".format(expected_role)))
                    else:  # if there are names before the action
                        # the closest preceding unmapped name
                        name = re.search(r'<name .*?>', chunk_before_action)
                        if name:
                            target_name = re.findall(r'<name .*?>', chunk_before_action)[-1]
                            if ";" not in target_name:  # condition that the target name is not mapped a role
                                line = line.replace(target_name,
                                                    target_name.replace(">", "; {}>".format(expected_role)))
                except:
                    pass

                # for receivers
                if action == 'Pass':
                    immediate_following_name = re.search(r'<name .*?>', chunk_after_action)
                    if immediate_following_name and immediate_following_name.span()[0] - a.span()[1] < 3:
                        # if following immediately after
                        target_name = re.findall(r'<name .*?>', chunk_after_action)[0]
                    if re.search(r'(?:to|for) <name .*?>', line[a.span()[1]:]):
                        # if has obvious receriver prepositions to/for in the rest of the line,
                        # not necessarily immediately following the action pass
                        target_name = re.findall(r'(?:to|for) <name .*?>', line[a.span()[1]:])[0]
                    if ";" not in target_name:  # condition that the target name is not mapped a role
                        line = line.replace(target_name, target_name.replace(">", "; {}>".format('receiver')))

        # when no actions except tackle but only gain/loss as results: default rush simple
        if len(names) != 0 and \
                len([a for a in actions if a.group() != '<action Tackle>']) == 0 and \
                len(results) != 0 and \
                all([bool(re.search(r'<result (?:Gain|Loss|Complete|Incomplete)>', r.group())) for r in results]):
            target_name = names[0].group()
            line = line.replace(target_name, target_name.replace(">", "; {}>".format('rusher')))

        # for tacklers: names following "tackled by" or names without actions and are close to the end of the sentence
        unroled_names = [un for un in re.finditer(r"<name.+?>", line) if
                         ';' not in un.group() or 'N/A' in un.group()]
        if len(actions) != 0:
            for un in unroled_names:
                if (re.search(r'<name.+tackler.*?>', line) and
                    0 < un.span()[0]-re.search(r'<name.+tackler.*?>', line).span()[1] < 8)\
                        or un.group() in chunks[-1]:
                    target_name = un.group()
                    line = line.replace(target_name, target_name.replace(">", "; {}>".format('tackler')))

        # finally, give N/A role unmapped names
        unroled_names = [un for un in re.finditer(r"<name.+?>", line) if ';' not in un.group() or 'N/A' in un.group()]
        for un in unroled_names:
            target_name = un.group()
            new_target_name = target_name
            # for i in range(3-len(target_name.split(";"))):
            new_target_name = new_target_name.replace(">", "; {}>".format('N/A'))
            line = line.replace(target_name, new_target_name)
        return line


    def rewind_standardize(self):
        roled_names = re.findall(r'<name .*?>', self.roled_line)
        unroled_names = re.findall(r'<name .*?>', self.named_line)
        line = self.named_line
        for i in range(len(unroled_names)):
            line = line.replace(unroled_names[i], roled_names[i])
        return line


#
# with open('named lines.txt', 'r') as f:
#     named_lines = f.read().split("\n")

# roled_lines = [PlayerRoleMapper(named_line).map_roles_to_names() for named_line in named_lines]

# standardized = [standardize(l) for l in named_lines]
# tagged = [tag_pos(s) for s in standardized]
# cleaned = [clean_up(s) for s in tagged]
# roled = [map_roles(s) for s in cleaned]
# d = pd.DataFrame({'named line': named_lines,
#                   'stnd line': standardized,
#                   'tagged': tagged,
#                   'cleaned': cleaned,
#                   'roled': roled
#                  })
# d.to_csv('xxxxx.csv', index=False)

# l = "<name davis> caught by <name brezina> for loss of 2"
# mapper = PlayerRoleMapper(l)
# mapper.assign_roles_to_names()
