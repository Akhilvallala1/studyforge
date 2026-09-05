/**
 * The focus-restoration guard, in every component that carries it.
 *
 * The house pattern: the focused control is never disabled mid-request, the buttons
 * are; a real `disabled` blurs the pressed button to the body, so focus has to be
 * placed again once the response lands. The restore acts only when the learner has not
 * moved since they sent, and the effect consumes the intent when it runs, so a
 * declined restore cannot leave it armed for a later commit.
 *
 * Both halves of the guard are asserted: that the restore FIRES when the learner has
 * not moved (focus left on the body by the disable, or, in ConceptTutor, still on the
 * control that sent), and that it DECLINES when the learner moved on. The decline half
 * has shipped broken four times and is the half a naive test omits.
 *
 * WHAT THIS SUITE DOES NOT PIN, deliberately and worth knowing: it asserts the
 * RESPONSE to a focus state, never the ARRIVAL of that state. jsdom does not blur a
 * control that becomes disabled, so the premise "a disabled button drops focus to the
 * body" is exercised nowhere in this file; requests are driven with fireEvent, which
 * never moves focus, and the body-focus state is real but test-established. If a
 * refactor or a browser change ever stopped the disable from blurring, every test here
 * would still pass while the restore never fired for button senders. The qa-tester's
 * browser pass is the only coverage of that trigger, not a nicety on top of this file.
 *
 * Written as mutation tests. Each was confirmed by making the change and watching the
 * right tests go red:
 *   - drop the guard, focus unconditionally      -> the three decline tests and both
 *     stale-intent tests fail (five, not three: the stale tests need the guard too)
 *   - drop the focus call                        -> the three body-restore tests and
 *     the keyboard-parity test fail
 *   - never clear the intent (ConceptTutor)      -> the tutor stale-intent test fails
 *   - clear the intent after the guard's early
 *     return (DeadlineForm)                      -> the deadline stale-intent test
 *     fails, via the reseed path that re-runs the effect without arming an intent
 *   - drop the focusAtSend disjunct (ConceptTutor) -> the keyboard-parity test fails,
 *     reintroducing the Ctrl+Enter bug ff876af fixed
 *   - drop the guard (DeleteCourseButton)        -> its decline test fails
 *   - drop the focus call (DeleteCourseButton)   -> both of its restore tests fail
 *   - drop the empty-state fallback in the id
 *     lookup (DeleteCourseButton)                -> only the empty-list test fails, which
 *     is what makes that test worth its own case rather than a variant of the first
 *   - never announce (DeleteCourseButton)        -> its live-region test fails
 *   - always render the shared-concept clause    -> the omit-when-zero test fails
 *   - drop the guard (QuizSection)               -> its decline test and its
 *     stale-intent test both fail
 *   - drop the focus call (QuizSection)          -> its four restore tests fail (both
 *     answer kinds, wrong and right)
 *   - revert the live region to the shape it
 *     replaced, an `announcement` fallback onto
 *     the snapshot (DeleteCourseButton)          -> exactly two fail: the mutation-shape
 *     test and the self-consumption test. Both arrival tests SURVIVE, correctly: the
 *     effect still sets the state, so the region settles on the same final text either
 *     way, and a text-content assertion cannot tell the two apart. Only an assertion
 *     about HOW the text arrived can, which is the whole reason the mutation-shape test
 *     exists as a separate case.
 *
 *     Two earlier versions of this entry were wrong, in opposite directions, and the
 *     second is the one worth keeping a record of. It claimed four failures and struck
 *     out the "settles on the same final text" clause as false. The clause was true. What
 *     was false was the mutation it had been measured against: the snapshot rendered with
 *     no state fallback at all, which is not the shape this replaced, is strictly
 *     harsher, and reddens SIX tests suite-wide including two in
 *     delete-confirmation.test.tsx. Neither reading was four. The note on the
 *     mutation-shape test itself had named the real shape all along, so the file
 *     contradicted itself for a round. Measure the mutation the code actually replaced,
 *     and cross-check it against what the rest of the file says that shape was.
 *   - drop the `handedOff` ref guard
 *     (DeleteCourseButton)                       -> only the self-consumption test
 *     fails, which is what earns that test its own case. Every other red test in this
 *     component comes from the `!handoffTitle` guard on the very next line of the same
 *     effect, and that guard cannot tell the writer of a handoff from a reader of one.
 *
 * One of those exposed a COUPLING worth recording, since the fix is the reusable part:
 * the delete decline test first synchronised on the live region, so dropping the
 * announcement turned it red for a reason that had nothing to do with focus. It now
 * relies on the act flush instead, and its ability to fail rests on the guard mutation
 * rather than on what it waits for. A test that waits on a neighbouring feature reports
 * that feature's bugs under its own name.
 *
 * Three clear-ordering mutants are KNOWN SURVIVORS, and honestly so:
 *   - ConceptTutor: its guard is a statement, not an early return, so the clear runs
 *     unconditionally wherever it sits and moving it changes nothing. The invariant
 *     there is non-consumption, which the stale-intent test pins.
 *   - DaysOffControl: its effect deps (pending, error, notice) change only inside
 *     run(), and run() overwrites the intent before any of them can commit, so
 *     clear-after-guard is behaviourally equivalent today. Killing it would mean
 *     reading component internals. The ordering stays a convention there until the
 *     component grows an intent-free effect path like DeadlineForm's reseed.
 *   - DeleteCourseButton: the same shape for a simpler reason. Its effect depends on
 *     `refreshing` alone, and the only thing that toggles it is onDeleted, which arms
 *     the intent on its way past. So there is no path that re-runs the effect with a
 *     stale intent still set, and clear-after-guard cannot be observed. The ordering is
 *     kept because it stops being equivalent the moment anything else drives that
 *     effect, which is exactly how DeadlineForm's reseed made it observable there.
 */

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ConceptTutor } from "@/components/ConceptTutor";
import { DaysOffControl } from "@/components/DaysOffControl";
import { DeadlineForm } from "@/components/DeadlineForm";
import { CourseDeletionProvider, DeleteCourseButton } from "@/components/DeleteCourseButton";
import { GenerateForm } from "@/components/GenerateForm";
import { QuizSection } from "@/components/QuizSection";
import type { TutorOutcome } from "@/lib/api";
import {
  answerQuiz,
  ApiError,
  deleteCourse,
  generateFromSources,
  getDeletionPreview,
  getGenerationLimits,
  getTutorConversation,
  removeDayOff,
  sendTutorMessage,
  setCourseDeadline,
} from "@/lib/api";
import type {
  AnswerResult,
  CourseDeletion,
  CoursePlan,
  DayOffRemoval,
  GenerateResult,
  SourceLimits,
} from "@/lib/types";

import { answerResult, conversation, deferred, plan, quizItem, quizProgress, tutorRow, turnOutcome } from "./fixtures";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getTutorConversation: vi.fn(),
  sendTutorMessage: vi.fn(),
  setCourseDeadline: vi.fn(),
  clearCourseDeadline: vi.fn(),
  addDayOff: vi.fn(),
  removeDayOff: vi.fn(),
  getDeletionPreview: vi.fn(),
  deleteCourse: vi.fn(),
  answerQuiz: vi.fn(),
  getGenerationLimits: vi.fn(),
  generateFromSources: vi.fn(),
}));

// Both forms refresh the route after a save; the refresh is a no-op here because the
// server data a refresh would carry is exactly what the props already hold.
//
// `replace` and `refresh` are hoisted rather than built fresh per `useRouter()` call
// so the "navigates to the course list" test below can assert on the very mock the
// component calls. A factory returning a new pair of `vi.fn()`s per call would leave
// this file with no handle on them, and there would be no single pair to hold a handle
// on: `useRouter()` is a hook, so it runs on every render, not once per mount. Hoisting
// is what makes every render hand back the same pair.
const { replace, refresh } = vi.hoisted(() => ({ replace: vi.fn(), refresh: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh, replace }),
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

  test("takes a Ctrl+Enter sender from the composer to the reply, though focus never touched the body", async () => {
    const { composer, turn } = await renderTutor();
    act(() => composer.focus());
    fireEvent.keyDown(composer, { key: "Enter", ctrlKey: true });
    // The composer is deliberately never disabled, so this send blurs nothing: focus
    // sits exactly where the learner left it, and the body test alone would call that
    // "moved on". This is the parity ff876af restored, and the case its focusAtSend
    // disjunct exists for.
    expect(composer).toHaveFocus();

    await act(async () => turn.resolve(turnOutcome(reply)));

    expect(
      screen.getByRole("region", { name: "Tutor reply" }),
      "a Ctrl+Enter sender who never left the composer has not moved on, and must reach the answer the way a button sender does",
    ).toHaveFocus();
  });

  test("declines to move focus when the learner moved on mid-request", async () => {
    const { composer, ask, turn } = await renderTutor();
    fireEvent.click(ask);
    // The learner went back to the box while the request was in flight. The box is not
    // where the send came from (the button was), so this is a move, not a stay.
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
    const view = render(<DeadlineForm plan={plan()} />);
    const date = screen.getByLabelText("Date");
    const label = screen.getByLabelText(/What to call it/);
    const submit = screen.getByRole("button", { name: "Set deadline" });
    const save = deferred<CoursePlan>();
    vi.mocked(setCourseDeadline).mockReturnValue(save.promise);
    fireEvent.change(date, { target: { value: "2026-12-01" } });
    return { date, label, submit, save, rerender: view.rerender };
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

  test("a declined restore consumes the intent rather than leaving it armed", async () => {
    const { label, submit, save, rerender } = renderForm();
    fireEvent.click(submit);
    act(() => label.focus());
    // A failure, not a success: the reseed step below needs a standing error for the
    // props change to clear, and failing is also the path where a learner most
    // plausibly wanders off mid-request.
    await act(async () => save.reject(new ApiError(400, "The deadline is in the past.")));
    await waitFor(() => expect(submit).toBeEnabled());
    expect(label).toHaveFocus();

    // The learner gives up and clicks away; focus lands nowhere.
    act(() => label.blur());
    // A route refresh delivers a deadline saved elsewhere. The reseed branch clears
    // the stale error, which re-runs the focus effect WITHOUT arming a fresh intent:
    // the one commit this component has where a leaked intent could fire. This is the
    // ordering that matters here and not in ConceptTutor, because this guard is an
    // early return: an intent cleared only after it would never be cleared on decline.
    rerender(<DeadlineForm plan={plan({ deadline: "2026-12-15", status: "active" })} />);

    expect(
      document.body,
      "the submit button must not seize focus on the reseed commit: the intent belonged to the failed save, and the declined restore should have consumed it",
    ).toHaveFocus();
  });
});

describe("DaysOffControl focus restoration", () => {
  const entry = { day: "2026-09-10", note: "Travelling", created_at: "2026-09-01T08:00:00Z" };

  function renderControl() {
    // `today` is a fixed literal on purpose, chosen before the fixture's day so the
    // entry renders in the upcoming list, which is where the Unmark button these tests
    // press lives. Deriving today from the clock would let the entry drift into the
    // collapsed past list one real morning and silently change which branch renders.
    render(<DaysOffControl daysOff={[entry]} today="2026-09-01" />);
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

/**
 * Deleting a course, where the control that was pressed is destroyed by its own success.
 *
 * The difference from the three components above: those keep a surviving sibling to
 * return to, and this one does not. The row unmounts, so the restore is owned by the
 * provider above the list, and its target is resolved by id at the moment it is needed
 * because WHICH target exists is exactly what the deletion changes. Deleting the last
 * course swaps the header's "New course" for the empty state's "Create your first
 * course", so a target captured beforehand would be the one element guaranteed to be gone.
 *
 * THE BODY-FOCUS PREMISE IS ESTABLISHED HERE TOO, and for a sharper reason than
 * elsewhere in this file. The confirming button is deliberately never disabled, so
 * nothing in jsdom blurs it: in a browser it is the row UNMOUNTING that drops focus to
 * the body, and jsdom will not unmount it here because the mocked refresh cannot change
 * the list these tests render. The blur below stands in for that unmount. It means these
 * tests pin the RESPONSE to focus being nowhere, never its arrival, and the browser pass
 * remains the only coverage of the trigger.
 */
describe("DeleteCourseButton focus restoration", () => {
  const preview: CourseDeletion = {
    course_id: 1,
    title: "Organic Chemistry",
    lessons: 12,
    lessons_completed: 8,
    quiz_items: 36,
    attempts: 47,
    concepts_total: 12,
    concepts_retired: 9,
    concepts_kept: 3,
    spend_usd: 0.42,
  };

  // Only the "navigate-to-list" tests below read sessionStorage or the hoisted
  // router mocks; clearing them for every test in this describe rather than only
  // those keeps the ordering of tests in this file from mattering to any of them.
  beforeEach(() => {
    window.sessionStorage.clear();
    replace.mockClear();
    refresh.mockClear();
  });

  async function renderList(options: { empty?: boolean; kept?: number } = {}) {
    vi.mocked(getDeletionPreview).mockResolvedValue({
      ...preview,
      concepts_kept: options.kept ?? preview.concepts_kept,
    });
    render(
      <CourseDeletionProvider>
        {/*
          Only one of these ever exists on the real page. Each test renders the one whose
          branch it is asserting, which is what makes the id lookup meaningful rather
          than a lucky match against whichever element happened to be first.
        */}
        {/*
          Plain anchors with a placeholder href, not next/link. What the restore needs
          from these is an id and focusability; routing is irrelevant here and a real
          page path would make the Next lint rule ask for a Link, which would drag the
          router into a test about focus.
        */}
        {options.empty ? (
          <a id="create-first-course" href="#top">
            Create your first course
          </a>
        ) : (
          <a id="new-course" href="#top">
            New course
          </a>
        )}
        <DeleteCourseButton courseId={1} title="Organic Chemistry" />
        <input aria-label="Search" />
      </CourseDeletionProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const confirm = await screen.findByRole("button", { name: "Delete permanently" });
    // That name also matches while the preview is still loading, when the button is
    // disabled and refuses the press. Clicking it there is a no-op, and every
    // assertion below then waits on an announcement that never comes: this is the
    // race that made this file fail about one run in eight on a loaded machine. See
    // tests/delete-confirmation.test.tsx for the defect it was reporting.
    await waitFor(() => expect(confirm).toBeEnabled());
    const removal = deferred<CourseDeletion>();
    vi.mocked(deleteCourse).mockReturnValue(removal.promise);
    return { confirm, removal };
  }

  test("sends focus to New course after a delete that left focus nowhere", async () => {
    const { confirm, removal } = await renderList();
    fireEvent.click(confirm);
    // Stands in for the row unmounting, which is what drops focus in a browser.
    act(() => confirm.blur());

    await act(async () => removal.resolve(preview));

    await waitFor(() =>
      expect(
        screen.getByRole("link", { name: "New course" }),
        "the deleted row is gone once the refresh lands, so the header control is the nearest thing the learner would act on next",
      ).toHaveFocus(),
    );
  });

  test("sends focus to Create your first course when the list empties", async () => {
    const { confirm, removal } = await renderList({ empty: true });
    fireEvent.click(confirm);
    act(() => confirm.blur());

    await act(async () => removal.resolve(preview));

    await waitFor(() =>
      expect(
        screen.getByRole("link", { name: "Create your first course" }),
        "deleting the last course removes the New course control entirely, so the restore has to find the empty state's link instead",
      ).toHaveFocus(),
    );
  });

  test("declines to move focus when the learner moved on mid-request", async () => {
    const { confirm, removal } = await renderList();
    const search = screen.getByLabelText("Search");
    fireEvent.click(confirm);
    // The learner started typing in the search box while the delete was in flight.
    act(() => search.focus());

    // Deliberately NOT synchronised on the live region: waiting for the announcement
    // would make this test fail whenever the announcement broke, which is a different
    // concern with its own test. Awaiting the act flushes the transition and the effect,
    // which is the only thing this assertion needs to have happened. That the test can
    // still fail is established by mutation, not by its wait: removing the guard turns
    // it red.
    await act(async () => removal.resolve(preview));

    expect(
      search,
      "a learner who moved to the search box mid-request keeps their place; the header link must not steal it",
    ).toHaveFocus();
  });

  test("names the deleted course in the live region", async () => {
    const { confirm, removal } = await renderList();
    fireEvent.click(confirm);

    await act(async () => removal.resolve(preview));

    await waitFor(() =>
      expect(
        screen.getByRole("status"),
        "the row announcing the deletion is gone by the time it would speak, so the region lives above the list",
      ).toHaveTextContent("Organic Chemistry deleted."),
    );
  });

  test("omits the shared-concept clause rather than saying nought more", async () => {
    await renderList({ kept: 0 });

    expect(screen.getByText(/9 concepts stop being reviewed/)).toBeInTheDocument();
    expect(
      screen.queryByText(/0 more/),
      "a learner with no concepts taught elsewhere should not be told about a category that is empty for them",
    ).not.toBeInTheDocument();
  });

  /*
   * The detail page's entry point: `afterDelete="navigate-to-list"`. This is the
   * regression risk T4 introduces, so it is pinned alongside the list's own restore
   * tests above rather than instead of them: those five `renderList`-based tests
   * render `DeleteCourseButton` with no `afterDelete` prop at all, and still pass
   * unmodified (confirmed by re-running the file against this change), which is what
   * pins the default staying "restore-focus". Mutation-verified the other direction
   * too: temporarily flipping the default parameter to "navigate-to-list" does NOT
   * turn every one of those five tests red, only "sends focus to New course after a
   * delete that left focus nowhere", "sends focus to Create your first course when
   * the list empties" and "names the deleted course in the live region" (the last
   * for its live-region text, not its focus assertion: with the default flipped,
   * `onDeleted` takes the replace branch, so neither `refresh` nor the in-place
   * announcement ever fires). "declines to move focus when the learner moved on
   * mid-request" and "omits the shared-concept clause rather than saying nought
   * more" stay green either way: the first because nothing moves focus under either
   * default, the second because it never confirms a delete at all. This test is what
   * would catch the default going the other way, since `replace` would then never be
   * called.
   *
   * Scope note, because the count above is easy to misread as a whole-suite figure: it
   * is about the five `renderList` tests in THIS file. The same flipped default also
   * reddens two in delete-confirmation.test.tsx, "refuses the press while loading, then
   * honours it once the preview is there" and "stays pressable while the delete itself
   * is in flight", so a full run shows five failures, not three.
   */
  test("navigates to the course list instead of restoring focus in place", async () => {
    vi.mocked(getDeletionPreview).mockResolvedValue(preview);
    const removal = deferred<CourseDeletion>();
    vi.mocked(deleteCourse).mockReturnValue(removal.promise);

    render(
      <CourseDeletionProvider>
        <DeleteCourseButton
          courseId={1}
          title="Organic Chemistry"
          afterDelete="navigate-to-list"
        />
      </CourseDeletionProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const confirm = await screen.findByRole("button", { name: "Delete permanently" });
    await waitFor(() => expect(confirm).toBeEnabled());
    fireEvent.click(confirm);

    await act(async () => removal.resolve(preview));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/courses"));
    expect(
      refresh,
      "the page being deleted has nowhere sensible to refresh back to",
    ).not.toHaveBeenCalled();
    // The announcement and the focus restore both belong to the destination page's
    // own provider instance now; see the handoff test below for that side of it.
    expect(window.sessionStorage.getItem("studyforge:deleted-course-title")).toBe(
      "Organic Chemistry",
    );
  });

  /*
   * The deleting page must not consume the handoff it just wrote.
   *
   * `subscribeToDeletionHandoff` is a no-op, so nothing NOTIFIES the source provider
   * that the key appeared, but its snapshot is re-read on any render it happens to do
   * before unmounting, and one is enough. Without the `handedOff` ref the source
   * consumes its own handoff: clears the key, announces on a page about to be replaced,
   * and leaves the list page to mount to an empty region.
   *
   * The state that drives the extra render WRAPS the provider deliberately. State held
   * inside it would not re-render the provider, so the test would pass against broken
   * code by never moving the thing it is meant to move.
   *
   * jsdom cannot say whether App Router really renders the source between `replace` and
   * unmount, and this does not claim it does. It pins that the component survives it
   * either way, which is cheaper than depending on the answer.
   *
   * Knob pushed the wrong way: dropping `if (handedOff.current) return` from the handoff
   * effect turns this red on the sessionStorage assertion, received null.
   */
  test("the deleting page does not consume the handoff it just wrote", async () => {
    vi.mocked(getDeletionPreview).mockResolvedValue(preview);
    const removal = deferred<CourseDeletion>();
    vi.mocked(deleteCourse).mockReturnValue(removal.promise);

    let rerenderSource = () => {};
    function SourcePage() {
      const [, setTick] = useState(0);
      rerenderSource = () => setTick((value) => value + 1);
      return (
        <CourseDeletionProvider>
          <DeleteCourseButton
            courseId={1}
            title="Organic Chemistry"
            afterDelete="navigate-to-list"
          />
        </CourseDeletionProvider>
      );
    }

    render(<SourcePage />);
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const confirm = await screen.findByRole("button", { name: "Delete permanently" });
    await waitFor(() => expect(confirm).toBeEnabled());
    fireEvent.click(confirm);

    await act(async () => removal.resolve(preview));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/courses"));

    // Still mounted, exactly as the source page is between `replace` and the navigation
    // committing. Put it through one render.
    await act(async () => {
      rerenderSource();
    });

    expect(
      window.sessionStorage.getItem("studyforge:deleted-course-title"),
      "the destination provider has not mounted yet, so the title must still be waiting",
    ).toBe("Organic Chemistry");
    expect(
      screen.getByRole("status").textContent,
      "announcing here would speak on a page that is being replaced",
    ).toBe("");
  });

  /*
   * The arrival side of the same handoff, exercised on a fresh provider instance the
   * way the real list page mounts one after `router.replace`: the announcement comes
   * from the same mount effect that reads `useSyncExternalStore`'s stashed title and
   * calls `setAnnouncement`, not from rendering that title directly (see the
   * mutation-shape test below for why that distinction is load-bearing), and the
   * focus restore is the SAME effect the in-place delete above uses, armed by the
   * mount effect that reads the handoff instead of by `onDeleted`.
   *
   * Mutation-verified: removing `wantsFocus.current = true` from the handoff effect
   * in DeleteCourseButton.tsx makes the focus assertion below fail (the link never
   * gains focus); removing the `if (!handoffTitle) return` guard's window.sessionStorage
   * write is not otherwise reachable here, since a mount with nothing stashed renders
   * an empty status region regardless, so this test's coverage of the effect starts
   * from the handoff being present, not from proving the guard's negative case.
   */
  test("announces and moves focus on arrival after a navigate-to-list delete elsewhere", async () => {
    window.sessionStorage.setItem("studyforge:deleted-course-title", "Organic Chemistry");

    render(
      <CourseDeletionProvider>
        <a id="new-course" href="#top">
          New course
        </a>
      </CourseDeletionProvider>,
    );

    await waitFor(() =>
      expect(
        screen.getByRole("status"),
        "a learner who just navigated here from the detail page must be told what happened, even though the delete itself happened on a page that no longer exists",
      ).toHaveTextContent("Organic Chemistry deleted."),
    );
    await waitFor(() =>
      expect(
        screen.getByRole("link", { name: "New course" }),
        "arriving here left focus on the body (a fresh navigation, not a click within this page), so the restore fires exactly as it would for an in-place delete",
      ).toHaveFocus(),
    );
    expect(
      window.sessionStorage.getItem("studyforge:deleted-course-title"),
      "consumed once, so a later reload of this same page cannot replay it",
    ).toBeNull();
  });

  /*
   * The arrival test above pins the FINAL text of the live region, which a region
   * rendered straight from `handoffTitle` would also satisfy: `toHaveTextContent`
   * only ever samples the settled DOM, so it cannot tell "born with this text" from
   * "mutated into having it", and a screen reader only speaks the second. This test
   * pins the shape instead, via the actual sequence of DOM operations React performs
   * (MutationObserver queues each mutation synchronously as it happens, independent
   * of when the callback drains, so this is not a timing gamble): the status node
   * must first be inserted by ITS PARENT with no text of its own, and only a LATER,
   * separate mutation whose target is the status node itself may be the one that
   * gives it content. A node that arrives already holding its final text produces
   * no second record targeting itself at all, which is what rendering from
   * `handoffTitle` directly used to do.
   *
   * Mutation-verified: reverting the live region to `announcement || (handoffTitle ?
   * ... : "")` (the shape this replaced) collapses the insertion and the content into
   * one record on the parent, and the assertion below finds no record targeting the
   * status node and fails.
   */
  test("announces arrival by mutating the live region, not by rendering it born full", async () => {
    window.sessionStorage.setItem("studyforge:deleted-course-title", "Organic Chemistry");
    const records: MutationRecord[] = [];
    const observer = new MutationObserver((list) => records.push(...list));
    observer.observe(document.body, { childList: true, subtree: true });

    render(
      <CourseDeletionProvider>
        <a id="new-course" href="#top">
          New course
        </a>
      </CourseDeletionProvider>,
    );
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Organic Chemistry deleted."),
    );
    observer.disconnect();

    const status = screen.getByRole("status");
    expect(
      records.some((record) => record.target === status),
      "the live region must be mutated after it exists in the DOM, or a screen reader has nothing to observe",
    ).toBe(true);
  });

  /*
   * An ordinary visit to `/courses`, nothing stashed: the `if (!handoffTitle)
   * return` guard in the handoff effect is what this pins. Without it, the effect
   * body still runs on this mount (`handoffTitle` is only ever checked, never
   * awaited), arming `wantsFocus.current` and announcing "null deleted." from a
   * title that was never there, for a learner who never deleted anything.
   *
   * Mutation-verified: deleting the guard line makes both assertions below fail
   * (focus moves to "New course" it never should have, and the status region picks
   * up "null deleted."). It turns three tests above red as well. The self-consumption
   * test goes red on its announcement assertion rather than its storage one, because an
   * unguarded effect announces "null deleted." on the source page's own first mount,
   * before any delete has happened; what that assertion then reads is the leftover of
   * that, not anything the delete did. The two "announces ... arrival" tests go red for
   * a related but distinct reason: their handoff effect re-runs a second
   * time once `setAnnouncement` triggers a re-render (`handoffTitle`'s snapshot has
   * gone null by then, since the removeItem earlier in the same effect body already
   * cleared it), and without the guard that second run overwrites the announcement
   * with "null deleted." too. That coupling is real but is not what this test is
   * for: this one isolates the plain-mount case, which the arrival tests cannot,
   * since both of them stash a title before rendering.
   */
  test("does not arm the deletion handoff on an ordinary mount with nothing stashed", () => {
    render(
      <CourseDeletionProvider>
        <a id="new-course" href="#top">
          New course
        </a>
      </CourseDeletionProvider>,
    );

    expect(
      screen.getByRole("link", { name: "New course" }),
      "nothing was deleted on this mount; only a delete handed off from elsewhere may move focus here",
    ).not.toHaveFocus();
    expect(
      screen.getByRole("status"),
      "an ordinary visit stashed nothing, so the live region has nothing to announce",
    ).toHaveTextContent("");
  });
});

/**
 * Checking a quiz answer, which unlike the four components above has two different
 * things a submission can leave behind, and picks its target accordingly.
 *
 * A wrong answer keeps the item open: the button survives, re-enabled and relabelled
 * "Try again", and the answer control (the text input, or the mcq's radios) is
 * re-enabled with it. That is what disables both those controls mid-request and drops
 * whichever held focus to the body, so the guard is the same body check as
 * ConceptPractice, DaysOffControl and DeadlineForm, and the target is the answer
 * control: the thing a keyboard learner needs a fresh attempt at, reached directly
 * rather than by blind-tabbing back to it from wherever the body left them.
 *
 * A RIGHT answer is the other shape. Solving the item unmounts the button entirely and
 * leaves the inputs disabled, so neither one exists to land on: the "Correct" message
 * is the only thing left in the item that a keyboard learner can be put on, so it
 * carries a `tabIndex={-1}` for exactly that. Which of the two targets a submission
 * wants is decided from `ever_correct`, not from this attempt's own `correct`: an item
 * solved earlier that takes another wrong attempt still has no button to return to.
 */
describe("QuizSection focus restoration", () => {
  function renderQuiz(kind: "mcq" | "short") {
    const item = quizItem({ id: 1, kind });
    const view = render(<QuizSection quiz={[item]} progress={quizProgress({ items: 1 })} />);
    const graded = deferred<AnswerResult>();
    vi.mocked(answerQuiz).mockReturnValue(graded.promise);
    return { item, graded, rerender: view.rerender };
  }

  /** A node outside the component, standing in for wherever a learner tabs off to. */
  function decoy(): HTMLButtonElement {
    const button = document.createElement("button");
    button.textContent = "elsewhere";
    document.body.appendChild(button);
    return button;
  }

  test("returns focus to the text input after a wrong short-answer that left focus on the body", async () => {
    const { graded } = renderQuiz("short");
    const input = screen.getByPlaceholderText("Your answer");
    fireEvent.change(input, { target: { value: "Ellipse" } });
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    // fireEvent never moves focus, so the body holds it: the state a real browser
    // reaches when disabling the pressed button and the re-enabled input blurs them.
    expect(document.body).toHaveFocus();

    await act(async () => graded.resolve(answerResult({ correct: false, expected: "Circular" })));

    expect(
      input,
      "a wrong answer leaves the input open to a retry, so a keyboard learner reaches a fresh answer directly instead of blind-tabbing back to it",
    ).toHaveFocus();
  });

  test("returns focus to the checked radio after a wrong mcq answer", async () => {
    const { item, graded } = renderQuiz("mcq");
    const option = screen.getByRole("radio", { name: item.options[0] });
    fireEvent.click(option);
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(document.body).toHaveFocus();

    await act(async () => graded.resolve(answerResult({ correct: false, expected: item.options[1] })));

    expect(
      option,
      "an mcq has no single answer control, so the checked radio is the one a retry needs: arrow keys move the selection from there without a blind tab back to the group",
    ).toHaveFocus();
  });

  test("moves focus to the Correct message once a right short answer unmounts the button", async () => {
    const { graded } = renderQuiz("short");
    const input = screen.getByPlaceholderText("Your answer");
    fireEvent.change(input, { target: { value: "Circular" } });
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(document.body).toHaveFocus();

    await act(async () => graded.resolve(answerResult({ correct: true, expected: "Circular" })));

    expect(
      screen.getByText("Correct"),
      "solving the item unmounts the button and leaves the input disabled, so the message is the only thing left for a keyboard learner to land on",
    ).toHaveFocus();
    expect(screen.queryByRole("button", { name: /Check answer|Try again/ })).not.toBeInTheDocument();
  });

  test("moves focus to the Correct message once a right mcq answer unmounts the button", async () => {
    const { item, graded } = renderQuiz("mcq");
    fireEvent.click(screen.getByRole("radio", { name: item.options[0] }));
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(document.body).toHaveFocus();

    await act(async () => graded.resolve(answerResult({ correct: true, expected: item.options[0] })));

    expect(screen.getByText("Correct")).toHaveFocus();
  });

  test("declines to move focus when the learner moved on mid-request", async () => {
    const { graded } = renderQuiz("short");
    const input = screen.getByPlaceholderText("Your answer");
    fireEvent.change(input, { target: { value: "Ellipse" } });
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    // The learner tabbed away from the item while the request was in flight.
    const elsewhere = decoy();
    act(() => elsewhere.focus());

    await act(async () => graded.resolve(answerResult({ correct: false, expected: "Circular" })));

    expect(
      elsewhere,
      "a learner who moved on mid-request is where they want to be; pulling them into the input is worse than the problem being fixed",
    ).toHaveFocus();
    elsewhere.remove();
  });

  test("a declined restore consumes the intent rather than leaving it armed for a later commit", async () => {
    const { item, graded, rerender } = renderQuiz("short");
    const input = screen.getByPlaceholderText("Your answer");
    fireEvent.change(input, { target: { value: "Ellipse" } });
    fireEvent.click(screen.getByRole("button", { name: "Check answer" }));
    const elsewhere = decoy();
    act(() => elsewhere.focus());

    await act(async () => graded.resolve(answerResult({ correct: false, expected: "Circular" })));
    expect(elsewhere).toHaveFocus();

    // Walk away from the decoy, back to the body, then force another commit of the
    // focus effect without a fresh submission arming it: a stale intent left armed by
    // the decline above would wrongly fire now, against a render it was never meant for.
    act(() => elsewhere.blur());
    rerender(<QuizSection quiz={[{ ...item }]} progress={quizProgress({ items: 1 })} />);

    expect(
      document.body,
      "the input must not seize focus on an unrelated later render: the intent belonged to the attempt that resolved, and the declined restore should have consumed it",
    ).toHaveFocus();
    elsewhere.remove();
  });
});

/**
 * GenerateForm has no single sender to restore focus to: rows are added and removed
 * freely, so the target is a different control on almost every commit. That is what the
 * four suites above have no equivalent of, and it is what most of these tests pin: which
 * TARGET the add and remove effects pick once the list has changed shape. The house
 * decline guard is here too, on the submit path, and is pinned alongside them.
 */
describe("GenerateForm focus restoration", () => {
  const SOURCE_LIMITS: SourceLimits = {
    max_sources: 20,
    max_total_chars: 200_000,
    max_upload_bytes: 20 * 1024 * 1024,
  };

  async function renderGenerateForm(extra?: ReactNode) {
    vi.mocked(getGenerationLimits).mockResolvedValue(SOURCE_LIMITS);
    const view = render(
      <>
        <GenerateForm />
        {extra}
      </>,
    );
    // Flushes the mount-time getGenerationLimits().then(...) inside act, rather than
    // leaving it to resolve as a stray microtask after a test's own assertions run.
    await act(async () => {});
    return view;
  }

  test("adding a text row focuses its new textarea", async () => {
    await renderGenerateForm();
    fireEvent.click(screen.getByRole("button", { name: "+ Add text" }));

    expect(
      screen.getByPlaceholderText(
        "Paste lecture notes, an article, documentation - anything you want to learn.",
      ),
      "the row just added is where the learner is about to type, so it should already have focus",
    ).toHaveFocus();
  });

  test("adding a url row focuses its new url input", async () => {
    await renderGenerateForm();
    fireEvent.click(screen.getByRole("button", { name: "+ Add URL" }));

    expect(
      screen.getByPlaceholderText("https://example.com/article"),
      "the row just added is where the learner is about to type, so it should already have focus",
    ).toHaveFocus();
  });

  test("removing a row focuses the Remove button of the row that slides into its place, crossing from a text row into a PDF row", async () => {
    const { container } = await renderGenerateForm();
    const addText = screen.getByRole("button", { name: "+ Add text" });
    fireEvent.click(addText);
    fireEvent.click(addText);

    const fileInput = container.querySelectorAll('input[type="file"]')[0];
    const pdfFile = new File(["%PDF-1.4"], "notes.pdf", { type: "application/pdf" });
    fireEvent.change(fileInput as HTMLInputElement, { target: { files: [pdfFile] } });
    await screen.findByText("notes.pdf");

    const removeButtons = screen.getAllByRole("button", { name: "Remove" });
    expect(removeButtons).toHaveLength(3);
    const pdfRemoveButton = removeButtons[2];

    // Removes the second (and last) text row. Its successor in the combined
    // [...rows, ...fileRows] order the form renders is the PDF row, not another text
    // row: a fix that hunted for a successor inside `rows` alone would find nothing here.
    fireEvent.click(removeButtons[1]);

    expect(
      pdfRemoveButton,
      "the PDF row's Remove button is the removed row's successor in combined order and must take focus",
    ).toHaveFocus();
  });

  test("removing the only row focuses the text-adding button", async () => {
    await renderGenerateForm();
    const addText = screen.getByRole("button", { name: "+ Add text" });
    fireEvent.click(addText);

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));

    expect(
      addText,
      "with no row left to hand focus to, the text-adding button is the nearest control to send it to",
    ).toHaveFocus();
  });

  test("a failed submit moves focus to the summary alert", async () => {
    await renderGenerateForm();
    fireEvent.click(screen.getByRole("button", { name: "Generate course" }));

    await waitFor(() =>
      expect(
        screen.getByRole("alert"),
        "a submit that fails must land the learner on the announced reason, not leave focus stranded on the button",
      ).toHaveFocus(),
    );
  });

  test("a second submit failing with the same message still moves focus back to the alert", async () => {
    await renderGenerateForm();
    const submit = screen.getByRole("button", { name: "Generate course" });

    fireEvent.click(submit);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveFocus());

    // The learner moves on before trying again. Nothing about the message is going to
    // change on a second, identical failure, which is exactly the case a plain
    // setSummaryError state update bails out of as a no-op: this must not silently fail
    // to re-announce, or to re-focus, just because the text is byte-identical.
    act(() => screen.getByRole("alert").blur());
    expect(document.body).toHaveFocus();

    fireEvent.click(submit);

    await waitFor(() =>
      expect(
        screen.getByRole("alert"),
        "a byte-identical second failure is still a fresh announcement and must reclaim focus, not leave it wherever the learner moved it since the first",
      ).toHaveFocus(),
    );
  });

  test("a synchronous failure moves focus to the alert from the submit button itself, not only from the body", async () => {
    await renderGenerateForm();
    const submit = screen.getByRole("button", { name: "Generate course" });
    act(() => submit.focus());
    // The empty-list guard returns before submitting is ever set, so the button is
    // never disabled and never blurs itself: activeElement is the button, not the
    // body. This is the focusAtSend disjunct of the guard, not the body one, and the
    // two prior "moves to alert" tests above never exercise it because fireEvent
    // leaves focus on the body by default.
    expect(submit).toHaveFocus();

    fireEvent.click(submit);

    await waitFor(() =>
      expect(
        screen.getByRole("alert"),
        "the learner sent from the button and never left it, so the restore must still land on the alert",
      ).toHaveFocus(),
    );
  });

  test("leaves focus alone when the learner moves on during a pending generation", async () => {
    const generation = deferred<GenerateResult>();
    vi.mocked(generateFromSources).mockReturnValue(generation.promise);
    const elsewhereRef = { current: null as HTMLInputElement | null };
    await renderGenerateForm(
      <input
        aria-label="Elsewhere"
        ref={(node) => {
          elsewhereRef.current = node;
        }}
      />,
    );
    const elsewhere = elsewhereRef.current;
    if (!elsewhere) throw new Error("elsewhere input did not mount");

    fireEvent.click(screen.getByRole("button", { name: "+ Add text" }));
    fireEvent.change(
      screen.getByPlaceholderText(
        "Paste lecture notes, an article, documentation - anything you want to learn.",
      ),
      { target: { value: "Some notes to learn from." } },
    );
    fireEvent.click(screen.getByRole("button", { name: "Generate course" }));

    // Generation takes 1 to 3 minutes by this form's own copy, plenty of time for the
    // learner to tab off to something else while it is still pending.
    act(() => elsewhere.focus());
    expect(elsewhere).toHaveFocus();

    await act(async () => {
      generation.reject(new ApiError(500, "Could not reach the server. Is the backend running?"));
      await generation.promise.catch(() => {});
    });

    expect(
      elsewhere,
      "the learner moved on before the result landed and matches neither focusAtSend nor the body, so the failed restore must leave them where they went",
    ).toHaveFocus();
  });

  test("the skip announcement pluralises its reason clause", async () => {
    const { container } = await renderGenerateForm();
    const fileInput = container.querySelectorAll('input[type="file"]')[0] as HTMLInputElement;

    fireEvent.change(fileInput, {
      target: {
        files: [
          new File(["notes"], "notes.txt", { type: "text/plain" }),
          new File(["slides"], "slides.pptx", { type: "application/vnd.ms-powerpoint" }),
        ],
      },
    });

    expect(
      (await screen.findByRole("status")).textContent,
      "the reason clause counts two files, so it must agree in number rather than read '2 not a PDF'",
    ).toContain("2 skipped: 2 not PDFs.");
  });

  test("the skip announcement keeps the singular reason clause for one file", async () => {
    const { container } = await renderGenerateForm();
    const fileInput = container.querySelectorAll('input[type="file"]')[0] as HTMLInputElement;

    fireEvent.change(fileInput, {
      target: { files: [new File(["notes"], "notes.txt", { type: "text/plain" })] },
    });

    expect(
      (await screen.findByRole("status")).textContent,
      "one file must stay singular, so the plural fix cannot be a blanket 's'",
    ).toContain("1 skipped: 1 not a PDF.");
  });
});
