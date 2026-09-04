"""The lesson payload names its owning course.

GET /lessons/{id} resolves a lesson by its own id and takes no course id, so a
client that nests the lesson under a course in its own URL has nothing to check
the pairing against. Without course_id, /courses/2/lessons/1 renders course 1's
lesson under course 2's heading with a 200, and the "back to course" link sends
the reader to a course the lesson is not in.
"""

from app import models
from app.db import SessionLocal


def _make_course(title, lesson_title):
    """Insert a one-module, one-lesson course. Returns (course_id, lesson_id)."""
    session = SessionLocal()
    try:
        course = models.Course(title=title, description="")
        module = models.Module(title="Module 1", position=0)
        lesson = models.Lesson(
            title=lesson_title, position=0, content=f"# {lesson_title}", concepts=[]
        )
        module.lessons.append(lesson)
        course.modules.append(module)
        session.add(course)
        session.commit()
        return course.id, lesson.id
    finally:
        session.close()


def test_lesson_payload_names_its_course(client):
    course_id, lesson_id = _make_course("Optimization", "Lesson A")

    body = client.get(f"/lessons/{lesson_id}").json()

    assert body["course_id"] == course_id


def test_two_courses_lessons_report_different_course_ids(client):
    """The discriminating case. A field that merely exists is not enough: it has to
    differ between courses, which is the only thing that lets a caller reject a
    mismatched pairing. Hardcoding either course's id would pass the test above."""
    first_course, first_lesson = _make_course("Optimization", "Lesson A")
    second_course, second_lesson = _make_course("Statistics", "Lesson B")

    first = client.get(f"/lessons/{first_lesson}").json()
    second = client.get(f"/lessons/{second_lesson}").json()

    assert first_course != second_course
    assert first["course_id"] == first_course
    assert second["course_id"] == second_course


def test_course_id_survives_a_lesson_in_a_later_module(client):
    """course_id is read through lesson.module, so a lesson that is not in the
    course's first module is the case where a wrong relationship hop would show."""
    session = SessionLocal()
    try:
        course = models.Course(title="Two modules", description="")
        for position, title in enumerate(("Module 1", "Module 2")):
            module = models.Module(title=title, position=position)
            module.lessons.append(
                models.Lesson(title=f"{title} lesson", position=0, content="", concepts=[])
            )
            course.modules.append(module)
        session.add(course)
        session.commit()
        course_id = course.id
        later_lesson = course.modules[1].lessons[0].id
    finally:
        session.close()

    body = client.get(f"/lessons/{later_lesson}").json()

    assert body["course_id"] == course_id
