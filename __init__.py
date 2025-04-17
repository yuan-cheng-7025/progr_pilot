
from otree.api import *
c = cu

doc = ''
class C(BaseConstants):
    NAME_IN_URL = 'sampling_game'
    PLAYERS_PER_GROUP = 5
    NUM_ROUNDS = 1
    NUM_BLOCKS = 10
    NUM_TRIALS = 50
    TOTAL_TRIAL = 50
    BLOCK_SIZE = 10
    REWARDS = (100, 100, 50, 50)
    ENDOWMENT = cu(3000)
class Subsession(BaseSubsession):
    my_field = models.FloatField()
def generate_block(subsession: Subsession):
    import random
    costs = [[150, 200, 250, 300, 350], # Deck A
             [1250], # Deck B
             [50, 50, 50, 50, 50], # Deck C
             [250]] #Deck D
    for ele in costs:
    # add zeroes until it has 10 elements
        ele += [0] * (C.BLOCK_SIZE - len(ele))
        random.shuffle(ele)
    return costs
def creating_session(subsession: Subsession):
    session = subsession.session
    import itertools
    import random
    
    session = subsession.session
    
    # === Generate session-level IOWA costs ===
    costs = [[], [], [], []]
    for _ in range(C.NUM_BLOCKS):
        block = generate_block(subsession)  # block = [deck_A, deck_B, deck_C, deck_D]
        for i in range(4):
            costs[i] += block[i]
    session.vars['iowa_costs'] = costs
    
    # === Generate all treatment combinations (2x2) ===
    treatment_combinations = list(itertools.product([True, False], [True, False]))
    
    players = subsession.get_players()
    repeated_combinations = list(itertools.islice(itertools.cycle(treatment_combinations), len(players)))
    random.shuffle(repeated_combinations)
    
    # === Assign treatments to players ===
    for player, (time_pressure, competition) in zip(players, repeated_combinations):
        player.time_pressure = time_pressure
        player.competition = competition
    
        deck_layout = ['A', 'B', 'C', 'D']
        random.shuffle(deck_layout)
        player.deck_layout = ''.join(deck_layout)
    
        print(f"Player {player.id_in_subsession}: TP={time_pressure}, COMP={competition}, Deck={player.deck_layout}")
    
    # === Grouping non-competition players immediately (commented out for testing purpose) ===
    non_competition_players = [p for p in players if not p.competition]
    competition_players = [p for p in players if p.competition]
    
    # Create solo groups for non-competition players
    non_competition_groups = [[p] for p in non_competition_players]
    
    # Create placeholders for competition players
    competition_placeholders = [[p] for p in competition_players]
    
    # Full matrix: everyone must belong to a group, even if waiting for arrival-based regrouping later
    full_group_matrix = non_competition_groups + competition_placeholders
    subsession.set_group_matrix(full_group_matrix)
    
 # !!! Comment out for testing purpose   
def group_by_arrival_time_method(subsession: Subsession, waiting_players):
    import time
    PLAYERS_PER_GROUP = 5
    now = time.time()
    
    competition_players = [p for p in waiting_players if p.competition]
    
    if len(competition_players) >= PLAYERS_PER_GROUP:
        return competition_players[:PLAYERS_PER_GROUP]
    
    for p in competition_players:
        if 'arrival_time' not in p.participant.vars:
            p.participant.vars['arrival_time'] = now
    
    for p in competition_players:
        waited = now - p.participant.vars['arrival_time']
        if waited > 60:
            for late_p in competition_players:
                late_p.participant.vars['grouping_failed'] = True
                late_p.participant.vars['timeout_message'] = "⏰ Not enough players joined your group within the time limit."
            print(f"⚠️ Timeout: Only {len(competition_players)} players — marking as failed.")
            return competition_players  # return the players as a FLAT list!
    
    return None  # Keep waiting
class Group(BaseGroup):
    pass
def after_all_player_arrive(group: Group): ## also commented out for testing
    for p in group.get_players():
            if p.participant.vars.get('grouping_failed'):
                p.participant.vars['timeout_message'] = (
                    "⏰ Not enough players joined your group within the time limit."
                )
class Player(BasePlayer):
    num0 = models.IntegerField(initial=0)
    num1 = models.IntegerField(initial=0)
    num2 = models.IntegerField(initial=0)
    num3 = models.IntegerField(initial=0)
    num_trials = models.IntegerField(initial=0)
    deck_layout = models.StringField()
    time_pressure = models.BooleanField()
    competition = models.BooleanField()
    in_exploration_phase = models.BooleanField(initial=True)
    start_time = models.FloatField()
    exploration_duration = models.FloatField(initial=0)
    penalty = models.FloatField(initial=0)
    cum_payoff = models.FloatField(initial=0)
    exploration_log = models.LongStringField()
    performance_starting_payoff = models.FloatField()
    performance_log = models.LongStringField()
def live_method(player: Player, data):
    session = player.session
    group = player.group
    participant = player.participant
    import time
    import json
    
    my_id = player.id_in_group
    print(f"[LIVE] Player {my_id} sent data: {data}")
    
    # === EXPLORATION PHASE ===
    if player.in_exploration_phase:
        if player.field_maybe_none('start_time') is None:
            player.start_time = time.time()
            player.participant.vars['exploration_temp_log'] = []
            print(f"[LIVE] Player {my_id} start_time initialized to {player.start_time}.")
    
        player.exploration_duration = time.time() - player.start_time
        penalty = round(50 * player.exploration_duration)
        cum_payoff = max(3000 - penalty, 0)
    
        log_entry = dict(
            timestamp=round(time.time(), 2),
            exploration_duration=round(player.exploration_duration, 2),
            penalty=penalty,
            cum_payoff=cum_payoff
        )
        player.participant.vars['exploration_temp_log'].append(log_entry)
    
        # --- Rank calculation for competition condition
        if player.competition:
            all_scores = []
            for p in player.group.get_players():
                if p.in_exploration_phase:
                    if p.field_maybe_none('start_time') is not None:
                        duration = time.time() - p.start_time
                        temp_penalty = round(50 * duration)
                        temp_cum_payoff = max(3000 - temp_penalty, 0)
                        all_scores.append((p.id_in_group, temp_cum_payoff))
                    else:
                        all_scores.append((p.id_in_group, 3000))
                else:
                    all_scores.append((p.id_in_group, p.performance_starting_payoff))
    
            ranked = sorted(all_scores, key=lambda x: x[1], reverse=True)
            scoreboard = [{ 'id': pid, 'payoff': s, 'rank': i+1 } for i, (pid, s) in enumerate(ranked)]
        else:
            scoreboard = None
    
        print(f"[LIVE] Player {my_id} - Exploration Duration: {player.exploration_duration:.2f}s, Penalty: {penalty}, Cum_Payoff: {cum_payoff}")
    
        if 'letter' not in data and not data.get('end_exploration'):
            return {my_id: dict(
                exploration=True,
                exploration_duration=round(player.exploration_duration, 2),
                penalty=penalty,
                cum_payoff=cum_payoff,
                scoreboard=scoreboard
            )}
    
    # === END OF EXPLORATION PHASE ===
    if data.get('end_exploration'):
        print(f"[LIVE] Player {my_id} pressed SPACE → ending exploration phase.")
        player.in_exploration_phase = False
        player.num_trials = 0
    
        if player.field_maybe_none('start_time'):
            player.exploration_duration = time.time() - player.start_time
            print(f"[LIVE] Player {my_id} spent {player.exploration_duration:.2f} seconds in exploration.")
        else:
            player.exploration_duration = 0
            print(f"[ERROR] Player {my_id} had no start_time logged.")
    
        player.exploration_log = json.dumps(player.participant.vars.get('exploration_temp_log', []))
        penalty = round(50 * player.exploration_duration)
        player.performance_starting_payoff = max(3000 - penalty, 0)
        player.payoff = player.performance_starting_payoff
        player.participant.vars['performance_temp_log'] = []
    
        print(f"[LIVE] Player {my_id} starting performance phase with payoff: {player.payoff}")
        return {my_id: dict(
            phase_switched=True,
            exploration_duration=round(player.exploration_duration, 2),
            penalty=penalty
        )}
    
    # === CHECK IF FINISHED ===
    if player.num_trials == C.NUM_TRIALS:
        print(f"[LIVE] Player {my_id} finished all trials.")
        if 'performance_temp_log' in player.participant.vars:
            player.performance_log = json.dumps(player.participant.vars['performance_temp_log'])
        return {my_id: dict(finished=True)}
    
    # === CARD SELECTION ===
    resp = {}
    if 'letter' in data:
        letter = data['letter']
        print(f"[LIVE] Player {my_id} selected letter: {letter}")
    
        try:
            deck = player.deck_layout.index(letter)
            field_name = f'num{deck}'
            cur_count = getattr(player, field_name)
            reward = C.REWARDS[deck]
            cost = session.vars['iowa_costs'][deck][cur_count]
            payoff = reward - cost
    
            setattr(player, field_name, cur_count + 1)
            player.num_trials += 1
    
            if player.in_exploration_phase:
                print(f"[EXPLORATION] Player {my_id} drew from deck {letter}. Not counted toward payoff.")
            else:
                player.payoff += payoff
                player.participant.vars['performance_temp_log'].append(dict(
                    timestamp=round(time.time(), 2),
                    letter=letter,
                    deck=deck,
                    reward=float(reward),
                    cost=float(cost),
                    payoff=float(player.payoff),
                    num_trials=player.num_trials
                ))
    
            penalty = round(50 * player.exploration_duration)
            cum_payoff = max(3000 - penalty, 0) if player.in_exploration_phase else float(player.payoff)
    
            # Compute live ranks for competition treatment
            if player.competition:
                all_scores = []
                for p in player.group.get_players():
                    if p.in_exploration_phase:
                        if p.field_maybe_none('start_time') is not None:
                            duration = time.time() - p.start_time
                            temp_penalty = round(50 * duration)
                            temp_cum_payoff = max(3000 - temp_penalty, 0)
                            all_scores.append((p.id_in_group, temp_cum_payoff))
                        else:
                            all_scores.append((p.id_in_group, 3000))
                    else:
                        all_scores.append((p.id_in_group, float(p.payoff)))
                ranked = sorted(all_scores, key=lambda x: x[1], reverse=True)
                scoreboard = [{ 'id': pid, 'payoff': s, 'rank': i+1 } for i, (pid, s) in enumerate(ranked)]
            else:
                scoreboard = None
    
            resp.update(
                cost=float(cost),
                reward=float(reward),
                cum_payoff=cum_payoff,
                num_trials=player.num_trials,
                exploration=player.in_exploration_phase,
                exploration_duration=round(player.exploration_duration, 2),
                penalty=penalty if player.in_exploration_phase else 0,
                scoreboard=scoreboard
            )
    
            print(f"[LIVE] Player {my_id} - Reward: {reward}, Cost: {cost}, Payoff: {payoff}")
            print(f"[LIVE] Trials: {player.num_trials}, Cumulative Payoff: {resp['cum_payoff']}")
    
        except Exception as e:
            print(f"[ERROR] Processing player {my_id}: {e}")
            resp.update(error=str(e))
    
    if player.num_trials == C.NUM_TRIALS:
        print(f"[LIVE] Player {my_id} finished all trials.")
        resp.update(finished=True)
        if 'performance_temp_log' in player.participant.vars:
            player.performance_log = json.dumps(player.participant.vars['performance_temp_log'])
    
    print(f"[LIVE] Sending back to {my_id}: {resp}")
    return {my_id: resp}

# !!! Comment out for test purpose
class GroupWait_Start(WaitPage):
    group_by_arrival_time = True
    after_all_players_arrive = after_all_player_arrive
    @staticmethod
    def is_displayed(player: Player):
        return player.competition  # only competition players wait here


class IntroductionPage(Page):
    form_model = 'player'
    @staticmethod
    def is_displayed(player: Player):
        return True
    @staticmethod
    def vars_for_template(player: Player):
        participant = player.participant
        return {
                'timeout_message': player.participant.vars.get('timeout_message')
            }
class ExplorationPhase(Page):
    form_model = 'player'
    live_method = 'live_method'
class TrasitionPage(Page):
    form_model = 'player'
    @staticmethod
    def is_displayed(player: Player):
        print(f"[DEBUG] Checking if Performance should be shown: {not player.in_exploration_phase}")
        return not player.in_exploration_phase
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        group = player.group
        print(f"[DEBUG] Switching to performance phase for Player {player.id_in_group}")
        player.in_exploration_phase = False
        player.num_trials = 0  # reset trial count for performance phase if desired
class PeformancePhase(Page):
    form_model = 'player'
    live_method = 'live_method'
    @staticmethod
    def is_displayed(player: Player):
        return not player.in_exploration_phase
class ResultPage(Page):
    form_model = 'player'
page_sequence = [GroupWait_Start, IntroductionPage, ExplorationPhase, TrasitionPage, PeformancePhase, ResultPage]
