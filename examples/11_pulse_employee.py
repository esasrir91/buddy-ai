"""
Example 11 — PULSE Virtual Employee

This example demonstrates how to:
1. Create a PULSE virtual employee with identity and skills
2. Run a document-based KT session
3. Start a live (human-interactive) KT session
4. Attend and process a meeting transcript
5. Receive and manage tasks
6. Generate a status update
7. Ask PULSE what it knows about a topic

Prerequisites:
    pip install "buddy-ai[tools]"
    export OPENAI_API_KEY=sk-...
"""
from buddy.models.openai import OpenAIChat
from buddy.pulse import (
    EmployeeProfile,
    KTSourceType,
    MeetingPlatform,
    PulseEmployee,
)

# ---------------------------------------------------------------------------
# 1. Create a PULSE employee
# ---------------------------------------------------------------------------
pulse = PulseEmployee(
    employee_profile=EmployeeProfile(
        full_name="Priya Sharma",
        role="Senior Backend Engineer",
        department="Engineering",
        team="Payments Platform",
        reporting_to="Arjun Nair",
        skills=["Python", "FastAPI", "PostgreSQL", "Redis"],
        domain_expertise=["payments", "authentication"],
        timezone="Asia/Kolkata",
        company_name="Acme Corp",
        bio="I'm a backend engineer specialising in high-throughput payment systems.",
    ),
    model=OpenAIChat(id="gpt-4o"),
)

print("=" * 60)
print(pulse.introduce_yourself())
print("=" * 60)


# ---------------------------------------------------------------------------
# 2. Onboarding — ingest company docs + meet team
# ---------------------------------------------------------------------------
# NOTE: In a real scenario, pass actual file paths or URLs.
# Here we skip actual docs to avoid file dependency.
# result = pulse.run_onboarding(
#     company_docs=["docs/architecture.pdf", "docs/runbook.md"],
#     team_members=[{"name": "Arjun Nair", "role": "Tech Lead"}],
# )
# print(result)


# ---------------------------------------------------------------------------
# 3. Document-based KT (async mode)
# ---------------------------------------------------------------------------
print("\n--- KT from text source ---")

sample_content = """
Authentication Service Overview
================================
Our auth service issues JWT access tokens with a 1-hour expiry. Alongside each
access token, a refresh token (30-day TTL) is issued and stored client-side.

Token Invalidation:
- On logout, the refresh token is added to a Redis blocklist.
- The blocklist entry TTL matches the token's remaining lifetime.
- Access tokens are short-lived so we don't blocklist them.

Token Rotation:
- Every time a refresh token is used to get a new access token,
  the refresh token itself is rotated (old one invalidated, new one issued).
- This prevents replay attacks.

Storage:
- Access tokens: memory only (not persisted)
- Refresh tokens: httpOnly cookie (client-side)
- Blocklist: Redis (key = token_jti, value = 1)
"""

kt_summary = pulse.take_kt(
    source=sample_content.encode(),
    source_type=KTSourceType.DOCUMENT,
    session_name="Auth Service Overview",
    knowledge_giver="Arjun Nair",
)
print(kt_summary.format_summary())


# ---------------------------------------------------------------------------
# 4. Live KT session (human-interactive)
# ---------------------------------------------------------------------------
print("\n\n--- Live KT Session ---")
session = pulse.start_live_kt(
    session_name="Payments Gateway Migration",
    knowledge_giver="Arjun Nair",
    source_type=KTSourceType.HUMAN_CHAT,
)

# Simulating the human-employee dialogue
turn = session.human_explains(
    "We're migrating from Stripe to Razorpay. The new integration uses webhooks "
    "for event processing — payment_success, payment_failed, refund_processed."
)
print(f"\nPRIYA: {turn.pulse_message}")
print(f"Confidence: {turn.confidence_score:.0%}")

turn = session.human_answers({
    "Q1": "Webhooks are verified using HMAC-SHA256 signature in the X-Razorpay-Signature header.",
    "Q2": "Idempotency is handled via event_id — we store processed IDs in Postgres.",
})
print(f"\nPRIYA: {turn.pulse_message}")
print(f"Confidence: {turn.confidence_score:.0%}")

if turn.ready_to_commit:
    summary = pulse.finalize_kt_session(session)
    print(f"\n✅ KT complete! Confidence: {summary.confidence_score:.0%}")
    print(f"Mental model: {summary.mental_model}")
else:
    print(f"\n[Session still running — {len(turn.questions)} questions pending]")


# ---------------------------------------------------------------------------
# 5. What do I know about X?
# ---------------------------------------------------------------------------
print("\n\n--- Knowledge Introspection ---")
knowledge = pulse.what_do_i_know_about("authentication tokens")
print(f"PRIYA's knowledge about auth tokens:\n{knowledge}")


# ---------------------------------------------------------------------------
# 6. Attend a meeting
# ---------------------------------------------------------------------------
print("\n\n--- Attend a Meeting ---")
transcript = """
Arjun: We need to complete the Razorpay migration by end of June.
Priya: I've completed the webhook integration. Still need to handle refunds.
Arjun: Can you take the refund flow as an action item?
Priya: Sure, I'll have it done by Friday.
Arjun: Also, we need to update the integration tests. Who can do that?
Dev: I'll take that.
"""

notes = pulse.attend_meeting(
    transcript=transcript,
    participants=["Arjun Nair", "Priya Sharma", "Dev"],
    platform=MeetingPlatform.ZOOM,
    title="Razorpay Migration Sync",
)
print(notes.format_summary())


# ---------------------------------------------------------------------------
# 7. Receive and manage tasks
# ---------------------------------------------------------------------------
print("\n\n--- Task Management ---")
task = pulse.receive_task(
    title="Implement Razorpay refund flow",
    description="Handle refund_processed webhook events from Razorpay, including idempotency checks.",
    assigned_by="Arjun Nair",
    priority="high",
    deadline="2026-06-27",
    tags=["payments", "razorpay", "backend"],
)
print(f"Task assigned: {task.format_brief()}")
task.start()
task.add_note("Started implementation — reviewing Razorpay refund webhook docs")

status = pulse.report_status(task_id=task.task_id)
print(f"\n{status.format_standup()}")


# ---------------------------------------------------------------------------
# 8. Launch the PULSE web server (commented out — starts a blocking server)
# ---------------------------------------------------------------------------
# from buddy.pulse.app import PulseApp
# PulseApp(employee=pulse).serve()
# Or just: buddy pulse start
