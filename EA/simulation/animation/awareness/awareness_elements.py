from element_utils import build_critical_section_with_finallyfrom animation.awareness.awareness_enums import AwarenessChannelfrom animation.awareness.awareness_tuning import AwarenessSourceRequest
def with_audio_awareness(*actors, sequence=()):
    awareness_modifiers = []

    def begin(_):
        for actor in actors:
            if actor is None:
                pass
            elif actor.is_sim:
                pass
            else:
                awareness_modifier = AwarenessSourceRequest(actor, awareness_sources={AwarenessChannel.AUDIO_VOLUME: 1})
                awareness_modifier.start()
                awareness_modifiers.append(awareness_modifier)

    def end(_):
        for awareness_modifier in awareness_modifiers:
            awareness_modifier.stop()

    return build_critical_section_with_finally(begin, sequence, end)
