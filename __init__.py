
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
    for _ in range(C.NUM_BLOCKS):  # Loop over blocks
        block = generate_block(subsession)  # block = [deck_A, deck_B, deck_C, deck_D]
        for i in range(4):  # Add each deck's values to costs
            costs[i] += block[i]
    session.vars['iowa_costs'] = costs
    
    # === Generate all treatment combinations (2x2) ===
    treatment_combinations = list(itertools.product([True, False], [True, False]))
    random.shuffle(treatment_combinations)  # Shuffle to randomize assignment
    
    players = subsession.get_players()
    repeated_combinations = list(itertools.islice(itertools.cycle(treatment_combinations), len(players)))
    
    for player, (time_pressure, competition) in zip(players, repeated_combinations):
        # Assign treatment
        player.time_pressure = time_pressure
        player.competition = competition
    
        # Assign individual deck layout
        deck_layout = ['A', 'B', 'C', 'D']
        random.shuffle(deck_layout)
        player.deck_layout = ''.join(deck_layout)
    
    print(f"Player {player.id_in_subsession}: TP={time_pressure}, COMP={competition}, Deck={player.deck_layout}")
    
class Group(BaseGroup):
    pass
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
    
        print(f"[LIVE] Player {my_id} - Exploration Duration: {player.exploration_duration:.2f}s, Penalty: {penalty}, Cum_Payoff: {cum_payoff}")
    
        if 'letter' not in data and not data.get('end_exploration'):
            return {my_id: dict(
                exploration=True,
                exploration_duration=round(player.exploration_duration, 2),
                penalty=penalty,
                cum_payoff=cum_payoff
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
    
                # 💡 FIX: converted Currency to float before logging
                player.participant.vars['performance_temp_log'].append(dict(
                    timestamp=round(time.time(), 2),
                    letter=letter,
                    deck=deck,
                    reward=float(reward),   # 💡 fix
                    cost=float(cost),       # 💡 fix
                    payoff=float(player.payoff),  # 💡 fix
                    num_trials=player.num_trials
                ))
    
            penalty = round(50 * player.exploration_duration)
            cum_payoff = max(3000 - penalty, 0) if player.in_exploration_phase else float(player.payoff)  # 💡 fix
    
            resp.update(
                cost=float(cost),     # 💡 fix
                reward=float(reward), # 💡 fix
                cum_payoff=cum_payoff,
                num_trials=player.num_trials,
                exploration=player.in_exploration_phase,
                exploration_duration=round(player.exploration_duration, 2),
                penalty=penalty if player.in_exploration_phase else 0
            )
    
            print(f"[LIVE] Player {my_id} - Reward: {reward}, Cost: {cost}, Payoff: {payoff}")
            print(f"[LIVE] Trials: {player.num_trials}, Cumulative Payoff: {resp['cum_payoff']}")
    
        except Exception as e:
            print(f"[ERROR] Processing player {my_id}: {e}")
            resp.update(error=str(e))
    
    # === FINAL CHECK AGAIN ===
    if player.num_trials == C.NUM_TRIALS:
        print(f"[LIVE] Player {my_id} finished all trials.")
        resp.update(finished=True)
        if 'performance_temp_log' in player.participant.vars:
            player.performance_log = json.dumps(player.participant.vars['performance_temp_log'])
    
    print(f"[LIVE] Sending back to {my_id}: {resp}")
    return {my_id: resp}
    
    
    
    
    
class IntroductionPage(Page):
    form_model = 'player'
class ExplorationPhrase(Page):
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
class PeformancePhrase(Page):
    form_model = 'player'
    live_method = 'live_method'
    @staticmethod
    def is_displayed(player: Player):
        return not player.in_exploration_phase
class ResultPage(Page):
    form_model = 'player'
page_sequence = [IntroductionPage, ExplorationPhrase, TrasitionPage, PeformancePhrase, ResultPage]