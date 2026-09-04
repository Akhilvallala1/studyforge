/**
 * The focus-restoration guard, in the three components that carry it.
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
import { describe, expect, test, vi } from "vitest";

import { ConceptTutor } from "@/components/ConceptTutor";
import { DaysOffControl } from "@/components/DaysOffControl";
import { DeadlineForm } from "@/components/DeadlineForm";
import { CourseDeletionProvider, DeleteCourseButton } from "@/components/DeleteCourseButton";
import { GenerateForm } from "@/components/GenerateForm";
import type { TutorOutcome } from "@/lib/api";
import {
  ApiError,
  deleteCourse,
  getDeletionPreview,
  getGenerationLimits,
  getTutorConversation,
  removeDayOff,
  sendTutorMessage,
  setCourseDeadline,
} from "@/lib/api";
import type { CourseDeletion, CoursePlan, DayOffRemoval, SourceLimits } from "@/lib/types";

import { conversation, deferred, plan, tutorRow, turnOutcome } from "./fixtures";

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
  getGenerationLimits: vi.fn(),
  generateFromSources: vi.fn(),
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
});

/**
 * GenerateForm has no single sender to restore focus to: rows are added and removed
 * freely, so the target is a different control on almost every commit. Unlike the four
 * suites above, the guard here is not "did the request land while I moved on", it is
 * "which control is the right one now that the list has changed shape", so these tests
 * pin the TARGET the effects pick, not a decline path.
 */
describe("GenerateForm focus restoration", () => {
  const SOURCE_LIMITS: SourceLimits = {
    max_sources: 20,
    max_total_chars: 200_000,
    max_upload_bytes: 20 * 1024 * 1024,
  };

  async function renderGenerateForm() {
    vi.mocked(getGenerationLimits).mockResolvedValue(SOURCE_LIMITS);
    const view = render(<GenerateForm />);
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
});
