# Design checklist

The design step of Planning follows this list for every Ticket that has a UI. It is done when each such Ticket has a
line `Design: <approved board or mock-up>` naming what the Owner approved. Generic rules only; the style and palette
are the Owner's answer to interview question 7.

## Rules for every screen

- Keep a 16 px margin between the content and every screen edge.
- Give every hotkey a visible button, so the screen works without a keyboard.
- Show no hotkey help on a phone: there is no keyboard to press them on.
- Label every board with its screen name and a state (for example `Home`, `Home empty`), and label each variant
  CHOSEN or REJECTED once the Owner has picked.
- Check the screen against the board before the Ticket is done, and list any deviation in the Handoff.

## Checks the end-to-end suite needs

- An accessibility scan (axe) of every page.
- A phone-width screenshot of every page.
- A test that no content sits closer than 16 px to a screen edge.

## Penpot calls

Every tool response stays in the context for the rest of the session, so keep Penpot calls few and small:

- One `execute_code` call per board, using helper functions inside the script.
- Return only a compact result (ids and names) from each call.
- Run `export_shape` once per board at the end, never between steps.
- Run `node --check` on the script before sending it.
- Edit with one call that targets shapes by id.

## Owner picks

Show the Owner one batch of variants per stage, only variants that already pass the automatic checks. Record the
chosen board in the Ticket's `Design:` line.
