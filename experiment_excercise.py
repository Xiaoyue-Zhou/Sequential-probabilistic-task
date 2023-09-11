import psynet.experiment
from psynet.asset import CachedAsset
from psynet.consent import NoConsent
from psynet.js_synth import Chord, JSSynth, Note, Rest, InstrumentTimbre
from psynet.modular_page import (
    AudioPrompt,
    Prompt,
    ModularPage,
    PushButtonControl,
    SliderControl
)
from psynet.page import InfoPage, SuccessfulEndPage
from psynet.timeline import Timeline, Module, join, conditional, CodeBlock
import numpy as np

# define dictionary of arpeggio
arpeggio = {'Major': [
    Note(60),
    Note(64),
    Note(67)
],
    'Minor': [
        Note(60),
        Note(63),
        Note(67)
    ]}

# ascending arpeggio
ascending_arpeggio = ModularPage(
    "js_synth",
    JSSynth(
        "The JS synthesizer plays ascending arpeggio",
        arpeggio['Major'],
    ),
    time_estimate=3
)

# major or minor arpeggio
major_or_minor = join(
    ModularPage(
        "choose scale",
        Prompt("Do you want major or minor arpeggio?"),
        PushButtonControl(choices=['Major', 'Minor']),
        time_estimate=5
    ),
    CodeBlock(
        lambda participant: participant.var.set("mode_chosen", participant.answer)
    ),
    conditional(
        "play chosen arpeggio",
        lambda participant: participant.var.mode_chosen == 'Major',
        ModularPage(
            "play chosen arpeggio",
            JSSynth(
                "The scale you chose is in Major mode",
                arpeggio['Major'],
            ),
            time_estimate=3
        ),
        ModularPage(
            "play chosen arpeggio",
            JSSynth(
                "The scale you chose is in Minor mode",
                arpeggio['Minor'],
            ),
            time_estimate=3
        ),
    )
)

# random sequence of tone drawn from scale
scale_note = [60, 62, 64, 65, 67, 69, 71, 72]
rand_idx = list(np.random.randint(len(scale_note), size=(1, 6))[0])
rand_tone = [Note(scale_note[idx]) for idx in rand_idx]

random_seq = ModularPage(
    "js_synth",
    JSSynth(
        "play a random sequence",
        rand_tone,
        timbre=InstrumentTimbre("piano")
    ),
    time_estimate=5
)


# Preference rating
preference_rating = ModularPage(
    "js_synth",
    JSSynth(
        "Rate your preference to the audio. Left(1) - most dislike, Right(4) - most like",
        rand_tone,
        timbre=InstrumentTimbre("piano")
    ),
    SliderControl(start_value=1, min_value=1, max_value=4,
                  n_steps=4),
    time_estimate=7
)


class Exp(psynet.experiment.Experiment):
    timeline = Timeline(
        NoConsent(),
        Module(
            "audio demos",
            ascending_arpeggio,
            major_or_minor,
            random_seq,
            preference_rating
        ),
        SuccessfulEndPage(),
    )
