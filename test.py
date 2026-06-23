from textwrap import dedent


def generate_logid_config():
    def k(keys):
        return f'type: "Keypress"; keys: [{", ".join(f'"{key}"' for key in keys)}];'

    def g(direction, keys):
        return (
            f'{{direction: "{direction}"; mode: "OnRelease"; action: {{{k(keys)}}};}}'
        )

    def button(cid, action):
        return f"{{cid: {hex(cid)}; action: {{{action}}};}}"

    def gest(actions_list):
        return f'type: "Gestures"; gestures: ({",".join(actions_list)});'

    buttons = [
        # Forward button
        button(0x56, k(["KEY_LEFTMETA"])),
        # Back button
        button(
            0x53,
            gest(
                [
                    g("None", ["KEY_C"]),
                    g("Right", ["KEY_G"]),
                    g("Left", ["KEY_D"]),
                    g("Up", ["KEY_F"]),
                    g("Down", ["KEY_ESC"]),
                ]
            ),
        ),
        # Gesture button
        button(0xC3, k(["KEY_LEFTMETA", "KEY_LEFTSHIFT"])),
        # Top button
        button(
            0xC4,
            gest(
                [
                    g("None", ["KEY_R"]),
                    g("Right", ["KEY_T"]),
                    g("Left", ["KEY_E"]),
                    g("Up", ["KEY_SPACE"]),
                    g("Down", ["KEY_B"]),
                ]
            ),
        ),
    ]
    return {
        "etc/logid.cfg": dedent(
            f"""\
            devices: ({{
                name: "MX Master 3S";
                smartshift: {{on: true; threshold: 15;}};
                hiresscroll: {{hires: true; invert: false; target: false;}};
                dpi: 6000;
                buttons: ({",".join(buttons)});
            }});
            """
        )
    }


print(generate_logid_config())

