/**
 * The summary error is the form's verdict on the sources as a whole, and unlike a row
 * error nothing about editing the form used to retire it. It was set on submit and
 * cleared on the next submit, so between the two it could assert something that had
 * stopped being true: qa-tester found the zero-source message still on screen after
 * adding a source, telling a learner who had just done the thing to go do it.
 *
 * The pair that matters most here is the file pick, and it is why this file has the
 * shape it does. A first version of the fix asked "did anything land?" by reading a
 * tally that ingestFiles fills in inside the setFileRows updater. React does not run an
 * updater until the next render, so that read was always zero and the retire never once
 * fired. Every test below passed anyway, because the suite had only the negative half:
 * a skip-only pick leaves the message up, which is equally true when the code does
 * nothing at all. The positive counterpart is what catches it, so both halves are here
 * for the pick, and for the label edit.
 *
 * Written as mutation tests. Each was applied, run, and reverted, and reddened exactly
 * the tests named beside it, and nothing else:
 *   - show any summaryError that is set,
 *     dropping the count comparison       -> "adding a source retires", "a pick that
 *                                            lands a file retires it", "a request-level
 *                                            failure, which marks nothing"
 *   - retire on every pick instead, the
 *     naive alternative fix               -> "a pick that adds nothing"
 *   - drop updateRow's patch.value
 *     condition, discarding on any edit   -> "editing only the optional label"
 *   - drop updateRow's discard entirely   -> "editing the source it complained about"
 *   - drop removeRow's discard            -> both "hidden by adding" resurrection tests
 *   - drop removeFileRow's discard        -> "hidden by removing a PDF"
 *
 * Two tests survive all six: "removing a source retires it" and "removing a PDF retires
 * it". The count comparison and the removal discards each cover those on their own, so
 * no single mutation can reach them; dropping the comparison and both discards together
 * reddens them, along with six others. They are kept because they pin what a learner
 * sees rather than either mechanism, and because they do fail on main.
 *
 * Against main's GenerateForm nine of the eleven fail. The two that pass there are the
 * two asserting a message STAYS up, which is main's behaviour for every case.
 *
 * Every count above was re-measured when the eleventh test was added, rather than
 * carried over: the first mutation and the combined one both reach it, and the tally
 * against main moved from eight of ten to nine of eleven because of it.
 */
import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { GenerateForm } from "@/components/GenerateForm";
import { ApiError, generateFromSources, getGenerationLimits } from "@/lib/api";
import type { SourceLimits } from "@/lib/types";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getGenerationLimits: vi.fn(),
  generateFromSources: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn(), replace: vi.fn() }),
}));

describe("GenerateForm summary error staleness", () => {
  const LIMITS: SourceLimits = {
    max_sources: 20,
    max_total_chars: 200_000,
    max_upload_bytes: 20 * 1024 * 1024,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  async function renderForm() {
    vi.mocked(getGenerationLimits).mockResolvedValue(LIMITS);
    const view = render(<GenerateForm />);
    // Flushes the mount-time getGenerationLimits().then(...) inside act.
    await act(async () => {});
    return view;
  }

  function submit() {
    fireEvent.click(screen.getByRole("button", { name: "Generate course" }));
  }

  /**
   * Asserted through the alert role rather than the copy. The role is what carries the
   * message to a screen reader, it is unique to this Callout (row errors are plain `p`
   * elements with no role), and a test spelling the sentence out would fail on a reword
   * that changed nothing about the behaviour being pinned.
   */
  function summaryAlert() {
    return screen.queryByRole("alert");
  }

  function pick(container: HTMLElement, file: File) {
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(input, { target: { files: [file] } });
  }

  const aPdf = () => new File(["%PDF-1.4 pretend"], "a.pdf", { type: "application/pdf" });
  const notAPdf = () => new File(["not a pdf"], "notes.docx", { type: "application/msword" });

  test("adding a source retires the message telling the learner to add one", async () => {
    await renderForm();
    submit();
    expect(summaryAlert(), "submitting with nothing to send is what raises it").toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "+ Add text" }));

    expect(
      summaryAlert(),
      "the learner has added the source it asked for, so it describes a state that is gone",
    ).not.toBeInTheDocument();
  });

  test("a pick that lands a file retires it", async () => {
    const { container } = await renderForm();
    submit();
    expect(summaryAlert()).toBeInTheDocument();

    pick(container, aPdf());

    expect(
      screen.getByLabelText("PDF: a.pdf"),
      "the file has to actually land for the rest of this test to mean anything",
    ).toBeInTheDocument();
    expect(
      summaryAlert(),
      "a PDF is now attached, so asking for one is no longer true",
    ).not.toBeInTheDocument();
  });

  test("a pick that adds nothing leaves the message standing", async () => {
    const { container } = await renderForm();
    submit();
    expect(summaryAlert()).toBeInTheDocument();

    pick(container, notAPdf());

    expect(
      screen.getByRole("status"),
      "the pick is still reported, so the learner learns the file was skipped",
    ).toBeInTheDocument();
    expect(
      summaryAlert(),
      "every file was skipped, so there is still no source and the instruction is still true",
    ).toBeInTheDocument();
  });

  test("removing a source retires it", async () => {
    await renderForm();
    fireEvent.click(screen.getByRole("button", { name: "+ Add text" }));
    submit();
    expect(summaryAlert()).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Remove" }));

    expect(
      summaryAlert(),
      "the row it pointed at is gone, so it cannot still be pointing at anything",
    ).not.toBeInTheDocument();
  });

  test("removing a PDF retires it", async () => {
    const { container } = await renderForm();
    fireEvent.click(screen.getByRole("button", { name: "+ Add text" }));
    pick(container, aPdf());
    submit();
    expect(
      summaryAlert(),
      "the blank text row is what raises it, with a PDF alongside so there is one to remove",
    ).toBeInTheDocument();

    // Text rows render before file rows, so the second Remove belongs to the PDF.
    fireEvent.click(screen.getAllByRole("button", { name: "Remove" })[1]);

    expect(screen.queryByLabelText("PDF: a.pdf")).not.toBeInTheDocument();
    expect(
      summaryAlert(),
      "the set of sources changed, which is the whole trigger, whatever kind of row went",
    ).not.toBeInTheDocument();
  });

  /**
   * The two below are the reason the removal handlers discard the error rather than
   * leaving it to the count comparison. Visibility is decided by comparing the current
   * source count against the count the submit judged, so a count that walks away and
   * comes back would bring the message back with it, un-announced and, in the second
   * case, false.
   */
  test("a message hidden by adding a source does not return when that source goes", async () => {
    await renderForm();
    submit();
    expect(summaryAlert()).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "+ Add text" }));
    fireEvent.click(screen.getByRole("button", { name: "Remove" }));

    expect(
      summaryAlert(),
      "the count is back where it started, but nothing has been submitted since, so there is no live verdict to show",
    ).not.toBeInTheDocument();
  });

  test("a message hidden by adding a PDF does not return when a text row goes", async () => {
    const { container } = await renderForm();
    fireEvent.click(screen.getByRole("button", { name: "+ Add text" }));
    submit();
    expect(
      summaryAlert(),
      "one blank text row, so the message on screen is the one about fixing a highlighted source",
    ).toBeInTheDocument();

    pick(container, aPdf());
    // Text rows render before file rows, so the first Remove belongs to the text row.
    fireEvent.click(screen.getAllByRole("button", { name: "Remove" })[0]);

    expect(screen.getByLabelText("PDF: a.pdf"), "only the text row was removed").toBeInTheDocument();
    expect(
      summaryAlert(),
      "one source again, the count the submit judged, but the highlighted row it named is gone, so returning here would point at nothing",
    ).not.toBeInTheDocument();
  });

  test("a message hidden by removing a PDF does not return when a row is added", async () => {
    const { container } = await renderForm();
    fireEvent.click(screen.getByRole("button", { name: "+ Add text" }));
    pick(container, aPdf());
    submit();
    expect(summaryAlert(), "two sources, one of them a blank text row").toBeInTheDocument();

    // File rows render after text rows, so the second Remove belongs to the PDF.
    fireEvent.click(screen.getAllByRole("button", { name: "Remove" })[1]);
    fireEvent.click(screen.getByRole("button", { name: "+ Add text" }));

    expect(
      summaryAlert(),
      "two sources again, and this is the removal path the other resurrection tests do not reach",
    ).not.toBeInTheDocument();
  });

  test("editing the source it complained about retires it", async () => {
    const { container } = await renderForm();
    fireEvent.click(screen.getByRole("button", { name: "+ Add text" }));
    submit();
    expect(summaryAlert(), "a blank row is what raises the fix-it message").toBeInTheDocument();

    const textarea = container.querySelector("textarea") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "Spaced repetition schedules reviews." } });

    expect(
      summaryAlert(),
      "the highlighted source has been fixed, which is exactly what it asked for",
    ).not.toBeInTheDocument();
  });

  test("editing only the optional label leaves it standing", async () => {
    const { container } = await renderForm();
    fireEvent.click(screen.getByRole("button", { name: "+ Add text" }));
    submit();
    expect(summaryAlert()).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Label (optional)"), { target: { value: "Lecture 1" } });

    const textarea = container.querySelector("textarea") as HTMLTextAreaElement;
    expect(textarea.value, "the source itself is still empty").toBe("");
    expect(
      summaryAlert(),
      "naming a blank source does not fill it, and this edit has already cleared the row's own error, so retiring here would leave nothing on screen saying the row is empty",
    ).toBeInTheDocument();
  });

  /**
   * A shape where retiring the message leaves nothing behind, which the SummaryError
   * comment names in words and this pins. The submit catch's plain-ApiError arm announces
   * and marks no row, so unlike the fix-it message it has no row error to fall back on:
   * the count moves and the whole thing is gone from the screen. Deliberately not called
   * THE one such shape: a 422 whose failures match no row by index and none by the ref
   * fallback also marks nothing. This is the one worth pinning because it needs no
   * contrived server response. Asserted on the TEXT rather than the alert role, since
   * "out of the alert" and "off the form" are different claims and it is the second one
   * being made.
   */
  test("adding a source clears a request-level failure, which marks nothing", async () => {
    const { container } = await renderForm();
    fireEvent.click(screen.getByRole("button", { name: "+ Add text" }));
    const textarea = container.querySelector("textarea") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "Spaced repetition schedules reviews." } });
    vi.mocked(generateFromSources).mockRejectedValue(new ApiError(503, "The service is away."));

    await act(async () => {
      submit();
    });
    expect(
      screen.getByText("The service is away."),
      "the request has to actually fail for the rest of this test to mean anything",
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "+ Add text" }));

    expect(
      screen.queryByText("The service is away."),
      "not merely out of the alert: no row carries it either, so the count change took it off the form outright",
    ).not.toBeInTheDocument();
  });
});
