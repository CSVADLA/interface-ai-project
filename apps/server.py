import os

from flask import Flask, render_template, request

app = Flask(__name__)

# Synthetic training data, not real member information.
MEMBERS = {
    "12345": {
        "name": "Alex Sample",
        "savings_balance": "1250.50",
    },
    "67890": {
        "name": "Jordan Demo",
        "savings_balance": "875.25",
    },
}


@app.get("/")
def home():
    member_id = request.args.get("member_id", "").strip()
    searched = "member_id" in request.args
    member = MEMBERS.get(member_id)

    delay_ms = 0

    if searched:
        delay_ms = min(
            int(os.getenv("MOCK_SEARCH_DELAY_MS", "0")),
            10000,
        )

    return render_template(
        "search.html",
        member_id=member_id,
        searched=searched,
        member=member,
        delay_ms=delay_ms,
    )


@app.get("/members/<member_id>")
def member_details(member_id):
    member = MEMBERS.get(member_id)

    if member is None:
        return "Member not found", 404

    return render_template(
        "member.html",
        member_id=member_id,
        member=member,
    )


@app.get("/members/<member_id>/savings")
def member_savings(member_id):
    member = MEMBERS.get(member_id)

    if member is None:
        return "Member not found", 404

    return render_template(
        "savings.html",
        member_id=member_id,
        member=member,
    )