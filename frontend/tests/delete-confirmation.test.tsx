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
 * - remove `disabled` from the confirming button -> the disabled assertion fails, and
 *   removing the assertion too makes the "not yet called" assertion fail instead
 * - widen it to `disabled={pending}` -> the post-resolve press is refused and the
 *   announcement never arrives, which is the behaviour the component documents it does
 *   NOT want, since disabling a focused control blurs it to the body
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

    await waitFor(() => expect(screen.getByRole("button", { name: "Deleting…" })).toBeEnabled());
    expect(
      screen.getByRole("button", { name: "Deleting…" }),
      "disabling it here would blur the learner to the body mid-request",
    ).toHaveFocus();

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
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(
      document.activeElement,
      "focus on the body means the learner has to tab from the top of the page again",
    ).not.toBe(document.body);
    expect(deleteCourse).not.toHaveBeenCalled();
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
});
