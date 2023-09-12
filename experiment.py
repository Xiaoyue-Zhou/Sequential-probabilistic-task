import psynet.experiment
from psynet.asset import LocalStorage
from psynet.consent import NoConsent
from psynet.js_synth import Chord, JSSynth, Note, Rest, InstrumentTimbre
from psynet.modular_page import (
    AudioPrompt,
    Prompt,
    ModularPage,
    PushButtonControl,
    SliderControl
)
from psynet.page import InfoPage, SuccessfulEndPage, VolumeCalibration
from psynet.timeline import (
    Timeline,
    Module,
    join,
    conditional,
    CodeBlock,
    for_loop,
    ProgressDisplay, ProgressStage, PageMaker)
from psynet.trial import Trial, Node

import numpy as np
import random


# --------------------------------- Transition matrix settings -------------------------------
def get_transition_matrix(network_type):
    # initialize output
    matrix = np.zeros(shape=(16, 16))
    if network_type == 'random':
        matrix[[1, 2, 4, 5], 0] = 1
        matrix[[0, 5, 6, 7, 10], 1] = 1
        matrix[[0, 3, 9, 11], 2] = 1
        matrix[[2, 7, 11], 3] = 1
        matrix[[0, 8, 9], 4] = 1
        matrix[[0, 1, 9, 12], 5] = 1
        matrix[[1, 10, 12], 6] = 1
        matrix[[1, 3, 10, 11], 7] = 1
        matrix[[4, 12], 8] = 1
        matrix[[2, 4, 5, 10, 14, 15], 9] = 1
        matrix[[1, 6, 7, 9, 14, 15], 10] = 1
        matrix[[2, 3, 7, 13], 11] = 1
        matrix[[5, 6, 8, 13, 14, 15], 12] = 1
        matrix[[11, 12, 15], 13] = 1
        matrix[[9, 10, 12], 14] = 1
        matrix[[9, 10, 12, 13], 15] = 1

    return matrix


transition_matrix = get_transition_matrix('random')
n_state = transition_matrix.shape[0]


#  --------------------------------- function definition ---------------------------------
def random_walk(seq_length, transition_matrix):
    # initialize output
    output = []
    for iTone in range(seq_length):
        if iTone == 0:
            curr_tone = np.random.randint(n_state)
        else:
            neighbors_line = list(transition_matrix[curr_tone, :])
            neighbors = [index for (index, value) in enumerate(neighbors_line) if value == 1]
            curr_tone = random.choice(neighbors)

        output.append(curr_tone)
    return output


def generate_trial_seq(transition_matrix, nTrial):
    seq_length = 2 + 4 * nTrial
    long_seq = random_walk(seq_length, transition_matrix)
    output = []
    for iTrial in range(nTrial):
        output.append(long_seq[iTrial * 4:iTrial * 4 + 6])
    return output


def generate_trial_seq_modified(transition_matrix, nTrial):
    trial_seq = generate_trial_seq(transition_matrix, nTrial)
    answer = np.random.choice(2, size=nTrial, replace=True)  # numpy.ndarray
    for iTrial in range(nTrial):
        if answer[iTrial] == 0:  # 0:answer = No, 1:answer = Yes
            # find irregular_signal
            fifth_tone = trial_seq[iTrial][-2]
            neighbors_line_fifth = transition_matrix[fifth_tone]
            not_neighbors = [index for (index, value) in enumerate(neighbors_line_fifth) if value == 0]
            irregular_signal = random.choice(not_neighbors)
            # assign irregular_signal to trial_seq
            trial_seq[iTrial][-1] = irregular_signal
    return trial_seq, answer


# ---------------------------------- Experiment settings -----------------------------
nTrial = 20
nTrial_per_block = 5

exposure_dur = 120  # 2 min * 60 s/min
tone_dur = 0.23
blank_dur = 0.2

midi_list = [60, 61, 62, 64, 66, 67, 69, 71,
                 72, 73, 74, 76, 78, 79, 81, 83]
random.shuffle(midi_list)  # TODO - move this randomisation into a CodeBlock, otherwise it'll happen every time experiment.py is loaded


def make_trial_definitions():
    trial_seq_modified, answer = generate_trial_seq_modified(transition_matrix=transition_matrix, nTrial=nTrial)

    # for exp adjustment
    trials = []
    for i, seq in enumerate(trial_seq_modified):
        trials.append(
            {
                "trial_number": i,
                "notes": [midi_list[k] for k in seq],
                "answer": answer[i]
            }
        )

    return trials



def exposure():
    return join(
        CodeBlock(lambda participant: participant.var.set(
            "exposure_sequence",
            random_walk(seq_length=int(exposure_dur // (tone_dur + blank_dur)), transition_matrix=transition_matrix)
        )),
        PageMaker(
            lambda participant: ModularPage(
                "exposure",
                JSSynth(
                    "please listen to the 2-min audio carefully, which is important for the following tasks.",
                    [Note(midi_list[i]) for i in participant.var.exposure_sequence],
                    timbre=InstrumentTimbre("piano"),
                    default_duration=tone_dur,
                    default_silence=blank_dur
                ),
                progress_display=ProgressDisplay(
                    stages=[ProgressStage(120,
                                          "Listen carefully ...",
                                          color='green',
                                          persistent=True)]
                )
            ),
            time_estimate=9,
        )
    )


# define ForcedChoiceTrial
class ForcedChoiceTrial(Trial):
    time_estimate = 10

    def show_trial(self, experiment, participant):
        choices = ['Yes', 'No']
        # random.shuffle(choices)  # Don't put randomising code within show_trial, it will cause bugs.
        # If you want randomisation, put it inside finalize_definition.
        return ModularPage(
            "audio_forced_choice",
            JSSynth(
                'Does the last tone meet your expectation?',
                [Note(pitch) for pitch in self.definition["notes"]],
                timbre=InstrumentTimbre("piano"),
                default_duration=0.23,
                default_silence=0.2
            ),
            PushButtonControl(choices=choices,
                              arrange_vertically=False)
        )

    def show_feedback(self, experiment, participant):
        choice_dict = {"No": 0, "Yes": 1}
        return conditional(
            "feedback",
            lambda participant: choice_dict[participant.answer] == int(self.definition["answer"]),
            InfoPage('Correct!',
                     time_estimate=0.7),
            InfoPage('Error!',
                     time_estimate=0.7)
        )


def trial_block():
    return for_loop(
        label="present a sequence of 6 tones and force a choice",
        iterate_over=lambda: make_trial_definitions(),
        logic=lambda trial_definition: ForcedChoiceTrial.cue(trial_definition),
        time_estimate_per_iteration=ForcedChoiceTrial.time_estimate,
        expected_repetitions=nTrial_per_block
    )


def rest():
    return InfoPage(
    "Please rest for a while. When you feel ready, please press 'Next' button to continue.",
    time_estimate=10,
)


def main_experiment():
    return Module(
        f"main_experiment",
        trial_block(),
        rest(),
        trial_block(),
        rest(),
    )


class Exp(psynet.experiment.Experiment):
    asset_storage = LocalStorage()
    timeline = Timeline(
        NoConsent(),
        VolumeCalibration(),
        InfoPage(""" 
                This experiment is consist of 2 stages. In the first stage, you will hear a sequence of tones which 
                lasts for 2 minutes. You should listen to it carefully, as it is important for the following tasks.
                In the second stage, you will be required to make some judgement on specific tone sequences. 
            """,
                 time_estimate=2),
        exposure(),
        InfoPage("""
                That's the end of stage 1. In stage 2, you will be required to make a series of judgement on the sequences you 
                hear. In each trial, we will present you with a sequence of 6 tones, which should be in the same musical style
                as the long sequence you heard in stage 1. You should decide whether the last tone in the sequence
                meets your expectation, considering the context provided by the previous tones. 
            """,
                 time_estimate=2),
        main_experiment(),
        SuccessfulEndPage(),
    )
