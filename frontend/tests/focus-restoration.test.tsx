/**
 * The focus-restoration guard, in the three components that carry it.
 *
 * The house pattern: the focused control is never disabled mid-request, the buttons
 * are; a real `disabled` blurs the pressed button to the body, so focus has to be
 * placed again once the response lands. The restore is guarded on
 * `document.activeElement === document.body`, and the intent is cleared BEFORE the
 * guard, so a learner who tabbed away mid-request consumes the intent rather than
 * leaving it armed for a later commit to fire.
 *
 * Both halves of the guard are asserted, deliberately: that the restore FIRES when the
 * blur left focus on the body, and that it DECLINES when the learner moved on. The
 * second half is the one that has shipped broken four times, and it is the half a
 * naive test omits, because a test that never moves focus cannot see it.
 *
 * jsdom does not blur a control when it becomes disabled, so these tests drive the
 * request with fireEvent (which never moves focus): focus genuinely rests on the body
 * for the fire cases, and is placed by hand for the decline cases. The real
 * disable-blur is a browser behaviour and stays the qa-tester's to see.
 *
 * Written as mutation tests. Each was confirmed by making the change and watching the
 * right test go red:
 *   - drop the body guard (focus unconditionally)     -> the decline tests fail
 *   - drop the focus call                              -> the restore tests fail
 *   - clear the intent AFTER the guard in ConceptTutor -> the stale-intent test fails
 */

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { ConceptTutor } from "@/components/ConceptTutor";
import { DaysOffControl } from "@/components/DaysOffControl";
import { DeadlineForm } from "@/components/DeadlineForm";
import type { TutorOutcome } from "@/lib/api";
import {
  getTutorConversation,
  removeDayOff,
  sendTutorMessage,
  setCourseDeadline,
} from "@/lib/api";
import type { CoursePlan, DayOffRemoval } from "@/lib/types";

import { conversation, deferred, plan, tutorRow, turnOutcome } from "./fixtures";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getTutorConversation: vi.fn(),
  sendTutorMessage: vi.fn(),
  setCourseDeadline: vi.fn(),
  clearCourseDeadline: vi.fn(),
  addDayOff: vi.fn(),
  removeDayOff: vi.fn(),
}));

// Both forms refresh the route after a save; the refresh is a no-op here because the
// server data a refresh would carry is exactly what the props already hold.
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

describe("ConceptTutor focus restoration", () => {
  async function renderTutor() {
    vi.mocked(getTutorConversation).mockResolvedValue(conversation([]));
    render(
      <ConceptTutor conceptKey="stability" conceptLabel="Stability" open onAnnounce={() => {}} />,
    );
    const composer = await screen.findByRole("textbox", { name: "Ask about Stability" });
    const ask = screen.getByRole("button", { name: "Ask" });
    const turn = deferred<TutorOutcome>();
    vi.mocked(sendTutorMessage).mockReturnValue(turn.promise);
    fireEvent.change(composer, { target: { value: "What grows stability?" } });
    return { composer, ask, turn };
  }

  const reply = tutorRow({
    answer: "Stability is the number of days until recall drops to ninety percent.",
  });

  test("moves focus to the fresh reply when the disable left focus on the body", async () => {
    const { ask, turn } = await renderTutor();
    fireEvent.click(ask);
    // fireEvent never moves focus, so the body holds it: the state a real browser
    // reaches when disabling the pressed button blurs it.
    expect(document.body).toHaveFocus();

    await act(async () => turn.resolve(turnOutcome(reply)));

    expect(
      screen.getByRole("region", { name: "Tutor reply" }),
      "with focus left on the body, the landed reply must take it, so a keyboard or screen reader user is taken to what arrived",
    ).toHaveFocus();
  });

  test("declines to move focus when the learner moved on mid-request", async () => {
    const { composer, ask, turn } = await renderTutor();
    fireEvent.click(ask);
    // The learner went back to the box while the request was in flight.
    act(() => composer.focus());

    await act(async () => turn.resolve(turnOutcome(reply)));

    expect(screen.getByRole("region", { name: "Tutor reply" })).toBeInTheDocument();
    expect(
      composer,
      "a learner who moved on mid-request is where they want to be; yanking them to the reply is worse than the problem being fixed",
    ).toHaveFocus();
  });

  test("a declined restore consumes the intent rather than leaving it armed", async () => {
    const { composer, ask, turn } = await renderTutor();
    fireEvent.click(ask);
    act(() => composer.focus());
    await act(async () => turn.resolve(turnOutcome(reply)));
    // The decline above must have CONSUMED the intent. Walk away from the box, then
    // cause another commit of the focus effect (an empty send sets the error state):
    // a still-armed intent would fire now, against a commit it was never meant for.
    act(() => composer.blur());
    fireEvent.click(ask);
    await screen.findByText("Type a question first.");

    expect(
      document.body,
      "the reply must not seize focus on a later commit: the intent belonged to the turn that landed, and the declined restore should have consumed it",
    ).toHaveFocus();
  });
});

describe("DeadlineForm focus restoration", () => {
  function renderForm() {
    render(<DeadlineForm plan={plan()} />);
    const date = screen.getByLabelText("Date");
    const label = screen.getByLabelText(/What to call it/);
    const submit = screen.getByRole("button", { name: "Set deadline" });
    const save = deferred<CoursePlan>();
    vi.mocked(setCourseDeadline).mockReturnValue(save.promise);
    fireEvent.change(date, { target: { value: "2026-12-01" } });
    return { date, label, submit, save };
  }

  test("returns focus to the submit button when the disable left focus on the body", async () => {
    const { submit, save } = renderForm();
    fireEvent.click(submit);
    expect(document.body).toHaveFocus();

    await act(async () => save.resolve(plan({ deadline: "2026-12-01", status: "active" })));

    await waitFor(() =>
      expect(
        submit,
        "with focus left on the body, the control that made the request must take it back",
      ).toHaveFocus(),
    );
  });

  test("declines to move focus when the learner moved on mid-request", async () => {
    const { label, submit, save } = renderForm();
    fireEvent.click(submit);
    // The learner went to name the deadline while the save was in flight.
    act(() => label.focus());

    await act(async () => save.resolve(plan({ deadline: "2026-12-01", status: "active" })));

    await waitFor(() => expect(submit).toBeEnabled());
    expect(
      label,
      "a learner typing the label mid-save must not have focus yanked back to the submit button",
    ).toHaveFocus();
  });
});

describe("DaysOffControl focus restoration", () => {
  const entry = { day: "2026-09-10", note: "Travelling", created_at: "2026-09-01T08:00:00Z" };

  function renderControl() {
    render(<DaysOffControl daysOff={[entry]} />);
    const date = screen.getByLabelText("Date");
    const note = screen.getByLabelText(/Why/);
    const unmark = screen.getByRole("button", { name: /^Unmark / });
    const removal = deferred<DayOffRemoval>();
    vi.mocked(removeDayOff).mockReturnValue(removal.promise);
    return { date, note, unmark, removal };
  }

  test("sends focus to the date field after an unmark that left focus on the body", async () => {
    const { date, unmark, removal } = renderControl();
    fireEvent.click(unmark);
    expect(document.body).toHaveFocus();

    await act(async () => removal.resolve({ day: entry.day, removed: true }));

    await waitFor(() =>
      expect(
        date,
        "the unmarked row is gone once the refresh lands, so the date field is the nearest control the learner would act on next",
      ).toHaveFocus(),
    );
  });

  test("declines to move focus when the learner moved on mid-request", async () => {
    const { note, unmark, removal } = renderControl();
    fireEvent.click(unmark);
    // The learner started writing a note for the next day off while the request ran.
    act(() => note.focus());

    await act(async () => removal.resolve({ day: entry.day, removed: true }));

    await waitFor(() => expect(unmark).toBeEnabled());
    expect(
      note,
      "a learner who moved into the note field mid-request keeps their place; the date field must not steal it",
    ).toHaveFocus();
  });
});
