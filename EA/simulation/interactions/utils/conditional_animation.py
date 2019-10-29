from animation.animation_utils import flush_all_animationsfrom element_utils import maybe, build_critical_section
def conditional_animation(interaction, value, xevt_id, animation):
    target = interaction.target
    did_set = False
    kill_handler = False

    def check_fn():
        current_state = target.get_state(value.state)
        return current_state is not value

    def set_fn(_):
        nonlocal did_set
        if did_set:
            return
        target.set_state(value.state, value)
        did_set = True

    if animation is None:
        return maybe(check_fn, set_fn)

    def set_handler(*_, **__):
        if kill_handler:
            return
        set_fn(None)

    def cleanup_asm(asm):
        nonlocal kill_handler
        if xevt_id is not None:
            kill_handler = True

    def reg_xevt(*_, **__):
        if xevt_id is not None:
            interaction.store_event_handler(set_handler, xevt_id)

    return maybe(check_fn, build_critical_section(reg_xevt, build_critical_section(animation(interaction, cleanup_asm=cleanup_asm), flush_all_animations, set_fn)))
