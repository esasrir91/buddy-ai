"""
Unit tests for the PULSE virtual employee module.
"""

from buddy.pulse.feedback import (
    FeedbackCategory,
    FeedbackEntry,
    FeedbackSentiment,
    FeedbackSystem,
)
from buddy.pulse.identity import (
    ColleagueBook,
    ColleagueRecord,
    EmployeeProfile,
    WorkingHours,
)
from buddy.pulse.kt import KTSession, KTSourceType
from buddy.pulse.meeting import (
    ActionItemPriority,
    MeetingNotes,
    TranscriptProcessor,
)
from buddy.pulse.memory import (
    ColleagueMemoryEntry,
    KTMemoryEntry,
    ProfessionalMemory,
)
from buddy.pulse.work import (
    StatusUpdate,
    TaskManager,
    TaskPriority,
    TaskStatus,
    WorkItem,
)

# ===========================================================================
# Identity tests
# ===========================================================================


class TestEmployeeProfile:
    def test_build_introduction(self):
        profile = EmployeeProfile(
            full_name="Priya Sharma",
            role="Backend Engineer",
            department="Engineering",
            company_name="Acme Corp",
            skills=["Python", "FastAPI"],
        )
        intro = profile.build_introduction()
        assert "Priya Sharma" in intro
        assert "Backend Engineer" in intro
        assert "Acme Corp" in intro

    def test_system_prompt_section(self):
        profile = EmployeeProfile(
            full_name="Alex Chen",
            role="Data Scientist",
            department="Data",
            reporting_to="Sarah Kim",
            skills=["Python", "ML"],
            timezone="US/Pacific",
        )
        prompt = profile.build_system_prompt_section()
        assert "Alex Chen" in prompt
        assert "Data Scientist" in prompt
        assert "Sarah Kim" in prompt
        assert "US/Pacific" in prompt

    def test_default_working_hours(self):
        hours = WorkingHours.standard_five_day()
        assert hours.monday.available is True
        assert hours.saturday.available is False

    def test_always_on_working_hours(self):
        hours = WorkingHours.always_on()
        assert hours.saturday.available is True
        assert hours.sunday.available is True


class TestColleagueBook:
    def test_add_and_find_colleague(self):
        book = ColleagueBook()
        book.add(ColleagueRecord(full_name="Arjun Nair", role="Tech Lead"))
        book.add(ColleagueRecord(full_name="Sarah Kim", role="PM"))

        found = book.find_by_name("arjun")
        assert found is not None
        assert found.role == "Tech Lead"

        not_found = book.find_by_name("nobody")
        assert not_found is None

    def test_find_by_role(self):
        book = ColleagueBook()
        book.add(ColleagueRecord(full_name="A", role="Backend Engineer"))
        book.add(ColleagueRecord(full_name="B", role="Frontend Engineer"))
        book.add(ColleagueRecord(full_name="C", role="DevOps"))

        engineers = book.find_by_role("engineer")
        assert len(engineers) == 2

    def test_list_names(self):
        book = ColleagueBook()
        book.add(ColleagueRecord(full_name="Alice", role="X"))
        book.add(ColleagueRecord(full_name="Bob", role="Y"))
        names = book.list_names()
        assert "Alice" in names
        assert "Bob" in names


# ===========================================================================
# Professional Memory tests
# ===========================================================================


class TestProfessionalMemory:
    def _make_kt_entry(self, domain: str, confidence: float = 0.9) -> KTMemoryEntry:
        return KTMemoryEntry(
            session_id="sess1",
            session_name=f"KT on {domain}",
            knowledge_giver="Arjun",
            domain=domain,
            key_concepts=["concept1"],
            mental_model=f"Understanding of {domain}",
            confidence_score=confidence,
            tags=[domain],
        )

    def test_store_and_recall_kt(self):
        mem = ProfessionalMemory()
        mem.store_kt(self._make_kt_entry("payments"))
        mem.store_kt(self._make_kt_entry("authentication"))

        results = mem.recall_kt(domain="payments")
        assert len(results) == 1
        assert results[0].domain == "payments"

    def test_kt_domains(self):
        mem = ProfessionalMemory()
        mem.store_kt(self._make_kt_entry("payments"))
        mem.store_kt(self._make_kt_entry("auth"))

        domains = mem.get_kt_domains()
        assert "payments" in domains
        assert "auth" in domains

    def test_colleague_memory(self):
        mem = ProfessionalMemory()
        mem.remember_colleague(
            ColleagueMemoryEntry(
                colleague_name="Arjun Nair",
                role="Tech Lead",
                interactions=["Code review discussion"],
            )
        )
        found = mem.recall_colleague("arjun")
        assert found is not None
        assert found.role == "Tech Lead"

    def test_professional_summary(self):
        mem = ProfessionalMemory()
        mem.store_kt(self._make_kt_entry("payments"))
        mem.remember_colleague(ColleagueMemoryEntry(colleague_name="X", role="Y"))

        summary = mem.professional_summary()
        assert summary["kt_sessions_completed"] == 1
        assert summary["colleagues_known"] == 1


# ===========================================================================
# KT Engine tests
# ===========================================================================


class TestKTSourceType:
    def test_human_mode_detection(self):
        assert KTSourceType.HUMAN_CHAT.is_human_mode is True
        assert KTSourceType.HUMAN_VOICE_CALL.is_human_mode is True
        assert KTSourceType.DOCUMENT.is_human_mode is False
        assert KTSourceType.URL.is_human_mode is False

    def test_async_mode_detection(self):
        assert KTSourceType.DOCUMENT.is_async_mode is True
        assert KTSourceType.HUMAN_CHAT.is_async_mode is False


class TestKTSessionJsonParsing:
    def test_parse_clean_json(self):
        data = KTSession._parse_json('{"key": "value", "num": 1}')
        assert data["key"] == "value"
        assert data["num"] == 1

    def test_parse_json_with_fences(self):
        data = KTSession._parse_json('```json\n{"key": "value"}\n```')
        assert data["key"] == "value"

    def test_parse_json_with_prefix_text(self):
        data = KTSession._parse_json('Here is the response:\n{"key": "val"}')
        assert data["key"] == "val"

    def test_parse_invalid_json_returns_empty(self):
        data = KTSession._parse_json("not json at all")
        assert data == {}

    def test_parse_json_with_plain_fences(self):
        data = KTSession._parse_json('```\n{"a": 1}\n```')
        assert data["a"] == 1


# ===========================================================================
# Meeting tests
# ===========================================================================


class TestTranscriptProcessor:
    def test_parse_simple_transcript(self):
        transcript = "Alice: Hello everyone\nBob: Hi Alice\nAlice: Let's start"
        entries = TranscriptProcessor.parse(transcript)
        assert len(entries) == 3
        assert entries[0].speaker == "Alice"
        assert entries[1].speaker == "Bob"

    def test_parse_timestamped_transcript(self):
        transcript = "[10:30] Alice: Good morning\n[10:31] Bob: Morning!"
        entries = TranscriptProcessor.parse(transcript)
        assert entries[0].timestamp == "10:30"
        assert entries[1].speaker == "Bob"

    def test_extract_participants(self):
        transcript = "Alice: Hi\nBob: Hello\nAlice: How are you"
        entries = TranscriptProcessor.parse(transcript)
        participants = TranscriptProcessor.extract_participants(entries)
        assert "Alice" in participants
        assert "Bob" in participants
        assert len(participants) == 2

    def test_parse_empty_transcript(self):
        entries = TranscriptProcessor.parse("")
        assert entries == []


class TestMeetingNotes:
    def _make_notes(self) -> MeetingNotes:
        from buddy.pulse.meeting import ActionItem

        return MeetingNotes(
            title="Sprint Planning",
            participants=["Priya", "Arjun", "Dev"],
            summary="Planned sprint 14 tasks and assigned owners.",
            action_items=[
                ActionItem(description="Fix login bug", owner="Priya", priority=ActionItemPriority.HIGH),
                ActionItem(description="Update API docs", owner="Arjun"),
            ],
            key_decisions=["Focus on auth module this sprint"],
        )

    def test_my_action_items(self):
        notes = self._make_notes()
        my_items = notes.my_action_items("Priya")
        assert len(my_items) == 1
        assert "login" in my_items[0].description

    def test_open_action_items(self):
        notes = self._make_notes()
        open_items = notes.open_action_items()
        assert len(open_items) == 2

    def test_format_summary(self):
        notes = self._make_notes()
        formatted = notes.format_summary()
        assert "Sprint Planning" in formatted
        assert "Fix login bug" in formatted


# ===========================================================================
# Work Engine tests
# ===========================================================================


class TestWorkItem:
    def test_lifecycle(self):
        task = WorkItem(
            title="Build payment webhook",
            description="Implement Razorpay webhook handler",
            priority=TaskPriority.HIGH,
        )
        assert task.status == TaskStatus.TODO
        task.start()
        assert task.status == TaskStatus.IN_PROGRESS
        task.complete()
        assert task.status == TaskStatus.DONE
        assert task.completed_at is not None

    def test_block(self):
        task = WorkItem(title="Task", description="Desc")
        task.block("Waiting for API credentials")
        assert task.status == TaskStatus.BLOCKED
        assert "Waiting for API credentials" in task.blockers

    def test_format_brief(self):
        task = WorkItem(title="My Task", description="Desc", priority=TaskPriority.CRITICAL)
        brief = task.format_brief()
        assert "CRITICAL" in brief
        assert "My Task" in brief


class TestTaskManager:
    def test_assign_and_retrieve(self):
        mgr = TaskManager("Priya")
        task = WorkItem(title="T1", description="Desc 1")
        mgr.assign(task)
        retrieved = mgr.get(task.task_id)
        assert retrieved is not None
        assert retrieved.title == "T1"

    def test_list_by_status(self):
        mgr = TaskManager("Priya")
        t1 = WorkItem(title="T1", description="D1")
        t2 = WorkItem(title="T2", description="D2")
        mgr.assign(t1)
        mgr.assign(t2)
        t1.start()
        in_progress = mgr.list_tasks(TaskStatus.IN_PROGRESS)
        assert len(in_progress) == 1
        assert in_progress[0].title == "T1"

    def test_task_summary(self):
        mgr = TaskManager("Priya")
        task = WorkItem(title="T", description="D")
        mgr.assign(task)
        summary = mgr.task_summary()
        assert summary["todo"] == 1
        assert summary["in_progress"] == 0


# ===========================================================================
# Feedback tests
# ===========================================================================


class TestFeedbackSystem:
    def test_receive_and_retrieve(self):
        fs = FeedbackSystem("Priya")
        entry = FeedbackEntry(
            given_by="Arjun",
            category=FeedbackCategory.COMMUNICATION,
            sentiment=FeedbackSentiment.POSITIVE,
            content="Great status updates!",
        )
        fs.receive(entry)
        recent = fs.recent(3)
        assert len(recent) == 1
        assert recent[0].given_by == "Arjun"

    def test_sentiment_distribution(self):
        fs = FeedbackSystem("Priya")
        fs.receive(FeedbackEntry(given_by="A", content="Good", sentiment=FeedbackSentiment.POSITIVE))
        fs.receive(FeedbackEntry(given_by="B", content="Needs work", sentiment=FeedbackSentiment.CONSTRUCTIVE))
        dist = fs.sentiment_distribution()
        assert dist["positive"] == 1
        assert dist["constructive"] == 1

    def test_actionable_items(self):
        fs = FeedbackSystem("Priya")
        fs.receive(FeedbackEntry(given_by="A", content="Fix this", sentiment=FeedbackSentiment.CONSTRUCTIVE))
        fs.receive(FeedbackEntry(given_by="B", content="Well done", sentiment=FeedbackSentiment.POSITIVE))
        items = fs.actionable_items()
        assert len(items) == 1
        assert items[0].content == "Fix this"

    def test_build_improvement_prompt(self):
        fs = FeedbackSystem("Priya")
        fs.receive(
            FeedbackEntry(
                given_by="Arjun",
                category=FeedbackCategory.COMMUNICATION,
                sentiment=FeedbackSentiment.CONSTRUCTIVE,
                content="Please be more concise in messages",
            )
        )
        prompt = fs.build_improvement_prompt()
        assert "concise" in prompt
        assert "communication" in prompt


# ===========================================================================
# StatusUpdate tests
# ===========================================================================


class TestStatusUpdate:
    def test_format_standup(self):
        update = StatusUpdate(
            employee_name="Priya Sharma",
            update_type="task_update",
            task_title="Razorpay Migration",
            what_i_did=["Completed webhook integration"],
            what_i_will_do=["Implement refund flow"],
            blockers=["Waiting for API keys"],
        )
        standup = update.format_standup()
        assert "Priya Sharma" in standup
        assert "webhook integration" in standup
        assert "refund flow" in standup
        assert "API keys" in standup
