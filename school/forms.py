from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import (
    ClassRoom,
    MarkColumn,
    MarkList,
    RemovalRequest,
    RosterColumn,
    RosterTable,
    Student,
    StudentFile,
)


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "የተጠቃሚ ስሙ ወይም የይለፍ ቃሉ ትክክል አይደለም።",
        "inactive": "ይህ አካውንት ንቁ አይደለም።",
    }


class ClassRoomForm(forms.ModelForm):
    class Meta:
        model = ClassRoom
        fields = ["name", "display_order", "is_active", "min_age", "max_age"]

    def clean(self):
        cleaned = super().clean()
        min_age = cleaned.get("min_age")
        max_age = cleaned.get("max_age")
        if min_age is not None and max_age is not None and min_age > max_age:
            raise forms.ValidationError("ዝቅተኛው ዕድሜ ከከፍተኛው ዕድሜ መብለጥ የለበትም።")
        return cleaned


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            "first_name", "father_name", "grandfather_name", "age", "birth_date",
            "registered_at", "phone", "parent_phone_1", "parent_phone_2",
            "background_notes", "classroom",
        ]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
            "registered_at": forms.DateInput(attrs={"type": "date"}),
            "background_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["classroom"].queryset = ClassRoom.objects.filter(is_active=True)


class AccountCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    classrooms = forms.ModelMultipleChoiceField(
        queryset=ClassRoom.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("ይህ የተጠቃሚ ስም ቀድሞ ተወስዷል።")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        username = self.cleaned_data.get("username", "")
        validate_password(password, user=User(username=username))
        return password


class AccountEditForm(forms.Form):
    classrooms = forms.ModelMultipleChoiceField(
        queryset=ClassRoom.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=True,
    )
    is_active = forms.BooleanField(required=False)


class ForcedPasswordChangeForm(SetPasswordForm):
    """No old-password confirmation — used right after login on a
    newly created or reset account (SRS §4.9)."""
    error_messages = {
        **SetPasswordForm.error_messages,
        "password_mismatch": "ሁለቱ የይለፍ ቃሎች አይመሳሰሉም።",
    }


class VoluntaryPasswordChangeForm(PasswordChangeForm):
    """Requires the current password — used when a user changes their
    password on their own initiative."""
    error_messages = {
        **PasswordChangeForm.error_messages,
        "password_mismatch": "ሁለቱ የይለፍ ቃሎች አይመሳሰሉም።",
        "password_incorrect": "የአሁኑ የይለፍ ቃል ትክክል አይደለም።",
    }


class MarkListForm(forms.ModelForm):
    class Meta:
        model = MarkList
        fields = ["name", "teacher", "subject", "year", "semester"]


class MarkColumnForm(forms.ModelForm):
    class Meta:
        model = MarkColumn
        fields = ["name", "max_score"]


class RosterTableForm(forms.ModelForm):
    class Meta:
        model = RosterTable
        fields = ["year", "semester"]


class RosterColumnForm(forms.ModelForm):
    class Meta:
        model = RosterColumn
        fields = ["subject_name"]


class RemovalRequestForm(forms.ModelForm):
    class Meta:
        model = RemovalRequest
        fields = ["reason"]
        widgets = {
            "reason": forms.Textarea(attrs={"rows": 3}),
        }


class StudentFileForm(forms.ModelForm):
    class Meta:
        model = StudentFile
        fields = ["file"]