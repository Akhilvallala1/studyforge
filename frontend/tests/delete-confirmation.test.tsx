/**
 * The confirming button must not accept a press before it can honour one.
 *
 * Opening the panel starts a preview request and sets `busy`, and `confirmDelete`
 * opens with `if (pending) return`. But the button rendered "Delete permanently" for
 * that whole window, because its label reads `busy && preview`, and `preview` is null
 * until the request lands. So the control said it was ready, looked ready, and threw
 * the press away: no delete, no error, no feedback of any kind. Press it again once
 * the preview has rendered and it works, which is exactly the shape of bug a learner
 * reports as "I clicked delete and nothing happened".
 *
 * This is where the suite's long-running flake came from. focus-restoration's
 * renderList did `findByRole("Delete permanently")` and clicked it, and that name
 * matched during the loading window too, so on a busy machine the click landed in the
 * dead zone and the announcement never came. The failure was real; only its
 * intermittency made it look like test noise. It is pinned here with a held promise
 * instead of a busy CPU, so it fails the same way every time.
 *
 * Mutation-verified, each confirmed by making the change and watching this go red:
 * - remove `disabled` from the confirming button (`disabled={false}`) -> only the
 *   `toBeDisabled()` assertion in the first test fails ("Received element is not
 *   disabled"). Removing that assertion too does NOT make the "not yet called"
 *   assertion fail in its place: `confirmDelete`'s own `if (pending) return` still
 *   refuses the press regardless of whether the button looks disabled, so with both
 *   removed all 4 tests pass. That gap is real and not one this file closes; the
 *   `toBeDisabled()` assertion above is the only thing here that would catch a
 *   dropped `disabled` prop, which is exactly why it stays even though the button
 *   would still (silently) refuse the click without it.
 * - widen it to `disabled={pending}` -> NOT this test. It still passes, because by
 *   the time the press below lands `busy` is already false and the button is
 *   enabled either way. The test that goes red is "stays pressable while the delete
 *   itself is in flight", on its `toBeEnabled()` wait for the "Deleting…" button:
 *   `pending` is true for the whole delete request, so that button is disabled and
 *   the `waitFor` times out. That is the behaviour the component documents it does
 *   NOT want, since disabling a focused control blurs it to the body.
 */
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { CourseDeletionProvider, DeleteCourseButton } from "@/components/DeleteCourseButton";
import { deleteCourse, getDeletionPreview } from "@/lib/api";
import type { CourseDeletion } from "@/lib/types";

import { deferred } from "./fixtures";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getDeletionPreview: vi.fn(),
  deleteCourse: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), push: vi.fn() }),
}));

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

describe("delete confirmation before the preview lands", () => {
  beforeEach(() => vi.clearAllMocks());

  test("refuses the press while loading, then honours it once the preview is there", async () => {
    const previewCall = deferred<CourseDeletion>();
    vi.mocked(getDeletionPreview).mockReturnValue(previewCall.promise);
    vi.mocked(deleteCourse).mockResolvedValue(preview);

    render(
      <CourseDeletionProvider>
        <DeleteCourseButton courseId={1} title="Organic Chemistry" />
      </CourseDeletionProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    // The panel is open and the preview is still in flight, held open deliberately.
    const confirm = await screen.findByRole("button", { name: "Delete permanently" });
    expect(
      confirm,
      "it cannot honour a press yet, so it must not present itself as able to take one",
    ).toBeDisabled();

    fireEvent.click(confirm);
    expect(
      deleteCourse,
      "the press was refused, and the learner has to be able to see that from the control",
    ).not.toHaveBeenCalled();

    await act(async () => previewCall.resolve(preview));

    await waitFor(() => expect(confirm).toBeEnabled());
    fireEvent.click(confirm);

    await waitFor(() => expect(deleteCourse).toHaveBeenCalledWith(1));
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Organic Chemistry deleted."),
    );
  });

  test("stays pressable while the delete itself is in flight", async () => {
    // The component disables on the LOADING window only, never on the request, because
    // this button holds focus by then and disabling a focused control drops it to body.
    vi.mocked(getDeletionPreview).mockResolvedValue(preview);
    const removal = deferred<CourseDeletion>();
    vi.mocked(deleteCourse).mockReturnValue(removal.promise);

    render(
      <CourseDeletionProvider>
        <DeleteCourseButton courseId={1} title="Organic Chemistry" />
      </CourseDeletionProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const confirm = await screen.findByRole("button", { name: "Delete permanently" });
    await waitFor(() => expect(confirm).toBeEnabled());

    fireEvent.click(confirm);

    // The `toBeEnabled()` wait above is the assertion that actually catches a
    // regression here (confirmed by mutating to `disabled={pending}`: this wait
    // times out and the test fails there, before `toHaveFocus()` below ever runs).
    // `toHaveFocus()` cannot do that job itself: jsdom does not blur a control when
    // it becomes disabled, so a wrongly-disabled button would still report
    // `toHaveFocus()` true here. Real disabled-blur is a browser behaviour this file
    // cannot exercise; it belongs to the qa-tester's Playwright pass (see
    // vitest.config.mts).
    await waitFor(() => expect(screen.getByRole("button", { name: "Deleting…" })).toBeEnabled());
    expect(screen.getByRole("button", { name: "Deleting…" })).toHaveFocus();

    await act(async () => removal.resolve(preview));
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Organic Chemistry deleted."),
    );
  });

  /*
   * Cancel unmounts the panel it is rendered in, so it destroys the focused element.
   * Nothing then claimed focus and it fell to the body, which is a keyboard learner
   * losing their place in a list they may have tabbed a long way down. Found in a
   * browser by QA, not by this suite: the confirm path was covered and the cancel path
   * was not.
   *
   * Mutation-verified: dropping `wantsTriggerFocus.current = true` from the Cancel
   * handler, and separately dropping the effect that reads it, each make this red with
   * activeElement as body.
   */
  test("puts focus back on the trigger when the confirmation is cancelled", async () => {
    vi.mocked(getDeletionPreview).mockResolvedValue(preview);

    render(
      <CourseDeletionProvider>
        <DeleteCourseButton courseId={1} title="Organic Chemistry" />
      </CourseDeletionProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));

    // Wait for the preview, since that is when the panel moves focus to the confirming
    // button. Cancelling before it lands would not be testing the same situation.
    const confirm = await screen.findByRole("button", { name: "Delete permanently" });
    await waitFor(() => expect(confirm).toBeEnabled());
    expect(confirm).toHaveFocus();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    const trigger = await screen.findByRole("button", { name: "Delete" });
    // No separate "activeElement is not document.body" assertion here: it cannot go
    // red on its own once `toHaveFocus()` above has passed (an element cannot have
    // focus while the body is the active element), so it would only ever be a dead
    // check dressed up as a second guarantee.
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(deleteCourse).not.toHaveBeenCalled();
  });

  /*
   * Cancel used to be enabled throughout, including during the delete itself. It is
   * not disabled there for the usual reason (a real `disabled` blurs the focused
   * confirming button to the body); Cancel never holds focus, so that risk does not
   * apply to it. It has to be disabled there anyway, because Cancel does not abort
   * the delete: pressing it mid-delete parks focus back on the trigger (see
   * `wantsTriggerFocus`) while `busy` is still true, and that trigger's own
   * `if (pending) return` would then swallow the next press with no feedback at all.
   *
   * Mutation-verified: widening `disabled={busy && !loadingPreview}` to
   * `disabled={false}` makes the "disabled during the delete" assertion below fail;
   * narrowing it to `disabled={busy}` (folding the preview window back in) makes
   * this test fail on its "enabled while the preview loads" assertion, and also
   * turns the "cancelling while the preview loads..." test below it red, since a
   * disabled button never fires its React `onClick` in jsdom (or a browser), so
   * `fireEvent.click(cancel)` there becomes a silent no-op rather than a cancel.
   */
  test("disables Cancel only while the delete itself is in flight", async () => {
    const previewCall = deferred<CourseDeletion>();
    vi.mocked(getDeletionPreview).mockReturnValue(previewCall.promise);
    const removal = deferred<CourseDeletion>();
    vi.mocked(deleteCourse).mockReturnValue(removal.promise);

    render(
      <CourseDeletionProvider>
        <DeleteCourseButton courseId={1} title="Organic Chemistry" />
      </CourseDeletionProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const cancel = await screen.findByRole("button", { name: "Cancel" });
    expect(cancel, "a slow preview must stay abandonable").toBeEnabled();

    await act(async () => previewCall.resolve(preview));
    expect(cancel, "idle with the preview shown, Cancel is a normal control").toBeEnabled();

    fireEvent.click(screen.getByRole("button", { name: "Delete permanently" }));
    await waitFor(() =>
      expect(
        cancel,
        "cancelling a delete already in flight cannot stop it, and would park focus on a trigger unable to honour a press until it finishes",
      ).toBeDisabled(),
    );

    await act(async () => removal.reject(new Error("boom")));
    await waitFor(() =>
      expect(cancel, "a failed delete clears busy, so Cancel is usable again").toBeEnabled(),
    );
  });

  /*
   * The same guard as the provider's own restore effect, and for the same reason: a
   * mouse click does not move focus onto the element it hits in Safari or Firefox
   * (jsdom matches that here too: `fireEvent.click` never focuses anything on its
   * own), so a learner who was already elsewhere when they clicked Cancel with a
   * mouse never left. Mutation-verified: deleting the
   * `if (document.activeElement !== document.body) return;` line from the cancel
   * effect makes this red, with focus landing on the trigger instead of staying on
   * the field the learner was using.
   */
  test("does not haul focus to the trigger when cancelling does not touch the learner's focus", async () => {
    vi.mocked(getDeletionPreview).mockResolvedValue(preview);

    render(
      <CourseDeletionProvider>
        <DeleteCourseButton courseId={1} title="Organic Chemistry" />
        <input aria-label="Search" />
      </CourseDeletionProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const confirm = await screen.findByRole("button", { name: "Delete permanently" });
    await waitFor(() => expect(confirm).toBeEnabled());

    const search = screen.getByLabelText("Search");
    act(() => search.focus());

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Delete permanently" })).not.toBeInTheDocument(),
    );
    expect(
      search,
      "a learner who moved on must not be hauled back to the trigger",
    ).toHaveFocus();
  });

  // The other rows must not fight for focus as they mount. `open` is false on every card
  // in a fresh list, so an effect keyed on that alone would have the last one win.
  test("does not steal focus when a card simply mounts", async () => {
    vi.mocked(getDeletionPreview).mockResolvedValue(preview);

    render(
      <CourseDeletionProvider>
        <DeleteCourseButton courseId={1} title="Organic Chemistry" />
        <DeleteCourseButton courseId={2} title="Linear Algebra" />
      </CourseDeletionProvider>,
    );

    await waitFor(() => expect(screen.getAllByRole("button", { name: "Delete" })).toHaveLength(2));
    expect(document.activeElement).toBe(document.body);
  });

  /*
   * Cancel used to leave `busy`/`loadingPreview` set until the abandoned preview
   * fetch itself settled, so the trigger's `if (pending) return` swallowed the very
   * next press for as long as that fetch happened to take, with nothing on screen to
   * explain why. Mutation-verified: reverting the Cancel handler to only clear
   * `open`/`preview`/`error` (dropping `setBusy(false)`/`setLoadingPreview(false)`)
   * makes this red, because the reopened panel never renders "Delete permanently" at
   * all, the trigger's own `if (pending) return` throwing the second click away.
   *
   * Clearing those flags is not enough by itself, which is what the second half
   * pins: the first (abandoned) preview can still resolve after a second one has
   * started, and its `finally` has to be a no-op for that generation, not a second
   * clear that resolves the wrong loading window. Mutation-verified: clearing
   * `busy`/`loadingPreview` in Cancel WITHOUT the generation guard (deleting the
   * `if (generationRef.current === generation)` check around the `finally` block,
   * while leaving Cancel's own clear in place) makes the second assertion below red:
   * the confirming button reports enabled after the stale first preview resolves,
   * one full step before the second preview (the one actually in flight) has
   * landed.
   */
  test("cancelling while the preview loads does not swallow the very next press", async () => {
    const first = deferred<CourseDeletion>();
    const second = deferred<CourseDeletion>();
    vi.mocked(getDeletionPreview)
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);

    render(
      <CourseDeletionProvider>
        <DeleteCourseButton courseId={1} title="Organic Chemistry" />
      </CourseDeletionProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    await screen.findByRole("button", { name: "Delete permanently" });

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    // No feedback distinguishes a swallowed press from a slow one, so the only way to
    // tell them apart is that a second preview actually starts loading.
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    const confirm = await screen.findByRole("button", { name: "Delete permanently" });
    expect(
      confirm,
      "the second preview must actually be loading, not silently refused",
    ).toBeDisabled();

    await act(async () => first.resolve(preview));
    expect(
      confirm,
      "the abandoned first preview must not resolve the second, unrelated loading window",
    ).toBeDisabled();

    await act(async () => second.resolve(preview));
    await waitFor(() => expect(confirm).toBeEnabled());
  });
});
