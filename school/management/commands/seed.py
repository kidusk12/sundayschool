import random
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from school import ethiopic, services
from school.models import (
    AttendanceSheet,
    ClassAssignment,
    ClassRoom,
    MarkColumn,
    MarkList,
    Profile,
    RosterColumn,
    RosterRow,
    RosterScore,
    Student,
)

CLASSES = [
    ("ቀዳማይ", 6, 9, 1),
    ("ካዕላይ", 10, 13, 2),
    ("ሣልሳይ", 14, 17, 3),
]

STUDENTS = [
    ("ኪዳኑ", "ተስፋዬ", "አበበ"),
    ("ሄርሞን", "ገብረ", "ማርያም"),
    ("ሳሙኤል", "ወልደ", "ሰማዕት"),
    ("ሰላማዊት", "በቀለ", "ኃይሉ"),
    ("ዳዊት", "አሰፋ", "ተክሌ"),
    ("ሩት", "ታደሰ", "ገብሬ"),
    ("ቤተልሔም", "ከበደ", "መንግሥቱ"),
    ("ናትናኤል", "ዘውዴ", "ጌታቸው"),
    ("ማርታ", "ሙሉጌታ", "ደስታ"),
    ("ኤልያስ", "አየለ", "ወርቁ"),
    ("ትዕግስት", "ፈቃዱ", "ሀብቴ"),
    ("ዮሴፍ", "ንጉሤ", "ዓለሙ"),
]

LEADERS = [
    ("leader1", ["ቀዳማይ", "ካዕላይ"]),
    ("leader2", ["ሣልሳይ"]),
]


class Command(BaseCommand):
    help = "Fills the database with sample data for local development."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="Seed-pass-2026", help="Password for all seeded accounts.")
        parser.add_argument("--force", action="store_true", help="Allow running when DEBUG is off.")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Refusing to seed with DEBUG off. Use --force if you really mean it.")

        random.seed(2026)
        password = options["password"]

        head = self._create_head(password)
        classrooms = self._create_classes()
        leaders = self._create_leaders(password, classrooms)
        self._create_students(head, classrooms)
        self._create_attendance(head, classrooms)
        self._create_marklists(head, classrooms)
        self._create_rosters(head, classrooms)

        self.stdout.write(self.style.SUCCESS("Seed complete."))
        self.stdout.write(f"  Head:    head / {password}   (no forced password change)")
        for username in leaders:
            self.stdout.write(f"  Leader:  {username} / {password}   (forced password change on first login)")

    # ------------------------------------------------------------------ users

    def _create_head(self, password):
        head_group, _ = Group.objects.get_or_create(name="Head")
        head, created = User.objects.get_or_create(username="head")
        if created:
            head.set_password(password)
            head.save()
        head.groups.add(head_group)
        Profile.objects.update_or_create(user=head, defaults={"must_change_password": False})
        return head

    def _create_classes(self):
        classrooms = {}
        for name, min_age, max_age, order in CLASSES:
            classroom, _ = ClassRoom.objects.get_or_create(
                name=name,
                defaults={"min_age": min_age, "max_age": max_age, "display_order": order},
            )
            classrooms[name] = classroom
        return classrooms

    def _create_leaders(self, password, classrooms):
        leader_group, _ = Group.objects.get_or_create(name="ClassLeader")
        usernames = []
        for username, class_names in LEADERS:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.save()
            user.groups.add(leader_group)
            Profile.objects.get_or_create(user=user)  # defaults to must_change_password=True
            for class_name in class_names:
                ClassAssignment.objects.get_or_create(user=user, classroom=classrooms[class_name])
            usernames.append(username)
        return usernames

    # --------------------------------------------------------------- students

    def _create_students(self, head, classrooms):
        class_list = list(classrooms.values())
        for index, (first, father, grandfather) in enumerate(STUDENTS):
            classroom = class_list[index % len(class_list)]
            if Student.objects.filter(
                first_name=first, father_name=father, grandfather_name=grandfather
            ).exists():
                continue
            Student.objects.create(
                first_name=first,
                father_name=father,
                grandfather_name=grandfather,
                age=random.randint(classroom.min_age, classroom.max_age),
                classroom=classroom,
                registered_by=head,
            )

    # ------------------------------------------------------------- attendance

    def _create_attendance(self, head, classrooms):
        year, month, _ = ethiopic.to_ethiopian(timezone.localdate())
        sundays = ethiopic.sundays_in_month(year, month)

        for classroom in classrooms.values():
            AttendanceSheet.objects.get_or_create(classroom=classroom, is_template=True)
            sheet, _ = AttendanceSheet.objects.get_or_create(
                classroom=classroom, ethiopian_year=year, ethiopian_month=month, is_template=False
            )
            for student in classroom.students.all():
                row, _ = services.add_student_to_sheet(sheet=sheet, student=student, user=head)
                for sunday in sundays:
                    if sunday > timezone.localdate():
                        continue
                    status = random.choices(
                        ["present", "absent", "permission"], weights=[7, 2, 1]
                    )[0]
                    services.mark_attendance(row=row, sunday_date=sunday, status=status, user=head)

    # -------------------------------------------------------------- mark lists

    def _create_marklists(self, head, classrooms):
        for classroom in classrooms.values():
            mark_list, created = MarkList.objects.get_or_create(
                classroom=classroom,
                name="ወንጌል",
                defaults={"teacher": "መምህር ሙሉጌታ", "subject": "ወንጌል", "year": "2018", "semester": "1"},
            )
            if not created:
                continue
            columns = [
                MarkColumn.objects.create(mark_list=mark_list, name="ፈተና", max_score=Decimal("50"), order=0),
                MarkColumn.objects.create(mark_list=mark_list, name="ተሳትፎ", max_score=Decimal("50"), order=1),
            ]
            for student in classroom.students.all():
                mark, _ = services.add_student_to_marklist(mark_list=mark_list, student=student, user=head)
                total = Decimal(0)
                for column in columns:
                    score = Decimal(random.randint(25, 50))
                    total += score
                    services.set_mark_column_score(mark=mark, column=column, score=score, user=head)
                services.set_mark_total(mark=mark, total=total, user=head)

    # ----------------------------------------------------------------- rosters

    def _create_rosters(self, head, classrooms):
        for classroom in classrooms.values():
            if classroom.rosters.exists():
                continue
            roster = services.create_roster(classroom=classroom, year="2018", semester="1", user=head)
            columns = [
                RosterColumn.objects.create(roster=roster, subject_name=name, order=order)
                for order, name in enumerate(["ወንጌል", "ትርጓሜ", "መዝሙር"])
            ]
            for row in RosterRow.objects.filter(roster=roster):
                for column in columns:
                    RosterScore.objects.create(
                        row=row, column=column, score=Decimal(random.randint(50, 100))
                    )
            services.calculate_roster(roster=roster, user=head)