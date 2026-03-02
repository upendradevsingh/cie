"""Expected LLM analysis outputs for each test transcript.

These are the "golden" mocked responses that the OpenAI mock returns.
They must be internally consistent (weighted scores match, etc.) and
serializable as JSON.
"""

import json
from typing import Any, Dict


def _hot_lead_analysis() -> Dict[str, Any]:
    """Solar Panel Hot Lead — expected high scores across the board."""
    return {
        "quality_scores": [
            {"parameter_name": "Opening & Greeting", "score": 8.5,
             "justification": "Professional greeting with name and company. Warm and welcoming tone."},
            {"parameter_name": "Need Discovery", "score": 9.0,
             "justification": "Excellent probing questions about roof type, area, current bills. Understood customer requirements thoroughly."},
            {"parameter_name": "Product Knowledge", "score": 9.0,
             "justification": "Detailed knowledge of system sizes, pricing, subsidies, warranty terms, and installation process."},
            {"parameter_name": "Objection Handling", "score": 8.5,
             "justification": "Addressed roof warranty concern with non-penetrating mounting system. Handled price objection with subsidy information."},
            {"parameter_name": "Pricing Discussion", "score": 8.0,
             "justification": "Transparent pricing with clear breakdown. Proactively mentioned government subsidy to reduce effective cost."},
            {"parameter_name": "Urgency Creation", "score": 7.5,
             "justification": "Referenced summer timeline and customer's own urgency. Could have added more time-sensitive offers."},
            {"parameter_name": "Next Steps", "score": 9.5,
             "justification": "Clear next step scheduled — site visit on Saturday at 10 AM. Confirmation via WhatsApp with documents."},
            {"parameter_name": "Call Control", "score": 8.0,
             "justification": "Good conversation flow. Let customer speak while guiding toward next steps."},
            {"parameter_name": "Active Listening", "score": 8.5,
             "justification": "Acknowledged competitor quote, paraphrased customer concerns about roof, and responded specifically."},
            {"parameter_name": "Closing Technique", "score": 9.0,
             "justification": "Successfully scheduled a site visit — strong commitment from the customer."},
        ],
        "overall_score": 85.5,
        "lead_intent_score": 88.0,
        "intent_classification": "hot",
        "intent_signals": [
            {"signal_name": "Budget Mentioned", "detected": True,
             "details": "Customer mentioned budget of 3-4 lakhs and compared with Tata Solar quote of 3.5L."},
            {"signal_name": "Timeline Discussed", "detected": True,
             "details": "Customer wants installation before May/summer. Agent confirmed mid-March timeline."},
            {"signal_name": "Decision Maker Identified", "detected": True,
             "details": "Customer confirmed she and her husband have discussed and are ready to move forward."},
            {"signal_name": "Competitor Comparison", "detected": True,
             "details": "Customer has quote from Tata Solar at 3.5 lakhs for 5kW system."},
            {"signal_name": "Specific Requirements Stated", "detected": True,
             "details": "1600 sq ft flat roof in Whitefield, 5-7kW system, non-penetrating installation."},
            {"signal_name": "Follow-up Requested", "detected": True,
             "details": "Customer proactively asked to schedule site visit."},
            {"signal_name": "Pricing Asked", "detected": True,
             "details": "Customer asked about subsidy and all-inclusive pricing."},
            {"signal_name": "Objections Raised", "detected": True,
             "details": "Roof waterproofing concern and budget threshold objection."},
        ],
        "persona": {
            "type": "Ready Buyer",
            "budget_score": 8.0,
            "authority_score": 9.0,
            "need_score": 9.0,
            "timeline_score": 9.0,
            "discovery_insights": [
                "Homeowner in Whitefield, Bangalore with 1600 sq ft flat roof",
                "Current electricity bill: Rs 12,000/month",
                "Has compared competitors (Tata Solar)",
                "Recently did roof waterproofing — concerned about damage",
                "Decision made jointly with husband — both aligned",
            ],
        },
        "action_items": [
            {"description": "Conduct site visit at customer's Whitefield home on Saturday March 8th at 10 AM",
             "category": "site_visit", "urgency": "immediate"},
            {"description": "Send WhatsApp confirmation with brochure, spec sheet, and subsidy info",
             "category": "send_info", "urgency": "immediate"},
            {"description": "Prepare customized 7kW system quote after site survey",
             "category": "follow_up", "urgency": "this_week"},
            {"description": "Follow up after site visit with formal proposal and financing options",
             "category": "follow_up", "urgency": "this_week"},
        ],
        "path_to_conversion": "Customer is highly engaged with clear budget, timeline, and authority. After site visit, send formal proposal with financing options. Emphasize the subsidy deadline and summer timeline to maintain urgency. Address any structural concerns from site survey promptly.",
        "rebuttals": [
            "For price comparison with Tata: Our 7kW system offers 40% more capacity than their 5kW quote at comparable effective cost after subsidy.",
            "For roof concerns: Provide photos of similar non-penetrating installations with before/after of waterproofing integrity.",
        ],
        "key_data_points": {
            "monthly_electricity_bill": "Rs 12,000",
            "roof_area": "1600 sq ft",
            "roof_type": "Flat concrete",
            "location": "Whitefield, Bangalore",
            "competitor_quote": "Tata Solar, 3.5L for 5kW",
            "preferred_system": "7kW",
            "site_visit_date": "Saturday March 8th, 10 AM",
        },
        "follow_up_urgency": "immediate",
        "call_summary": "Highly productive call with homeowner Priya Sharma interested in 7kW solar installation. Customer has budget (3-4L range), authority (discussed with husband), clear need (12K monthly bills), and urgent timeline (before summer). Site visit scheduled for Saturday. Strong conversion potential.",
    }


def _warm_lead_analysis() -> Dict[str, Any]:
    """SaaS Demo Warm Lead — medium scores, authority gap."""
    return {
        "quality_scores": [
            {"parameter_name": "Opening & Greeting", "score": 7.0,
             "justification": "Friendly opening but could have been more structured. Jumped to demo quickly."},
            {"parameter_name": "Need Discovery", "score": 8.0,
             "justification": "Good discovery of pain points — Jira complexity for non-tech teams, 150 employees. Could have quantified time wasted."},
            {"parameter_name": "Product Knowledge", "score": 8.5,
             "justification": "Strong demo with clear feature explanations. Good integration knowledge."},
            {"parameter_name": "Objection Handling", "score": 7.0,
             "justification": "Handled budget concern with ROI document offer. Did not address the authority gap directly."},
            {"parameter_name": "Pricing Discussion", "score": 7.5,
             "justification": "Transparent pricing with discount option. Proactively offered annual billing savings."},
            {"parameter_name": "Urgency Creation", "score": 5.0,
             "justification": "No time-sensitive offers or deadlines mentioned. Missed opportunity to create urgency."},
            {"parameter_name": "Next Steps", "score": 7.5,
             "justification": "Follow-up call with CTO scheduled for next week. Trial set up. Could have been more specific on date."},
            {"parameter_name": "Call Control", "score": 7.0,
             "justification": "Good flow but let the demo run long before addressing decision-making process."},
            {"parameter_name": "Active Listening", "score": 7.5,
             "justification": "Picked up on cross-team visibility need and tailored demo accordingly."},
            {"parameter_name": "Closing Technique", "score": 6.0,
             "justification": "Soft close with trial and follow-up call. No attempt to get conditional commitment."},
        ],
        "overall_score": 58.0,
        "lead_intent_score": 62.0,
        "intent_classification": "warm",
        "intent_signals": [
            {"signal_name": "Budget Mentioned", "detected": True,
             "details": "CTO approval needed for purchases over 50K/year. Annual cost is 1.54L."},
            {"signal_name": "Timeline Discussed", "detected": False,
             "details": "No specific implementation timeline discussed."},
            {"signal_name": "Decision Maker Identified", "detected": True,
             "details": "CTO Anand is the final decision maker. Vikram is the evaluator."},
            {"signal_name": "Competitor Comparison", "detected": True,
             "details": "Currently using Jira and Google Sheets — looking for unified alternative."},
            {"signal_name": "Specific Requirements Stated", "detected": True,
             "details": "40 active users, Slack + GitHub integrations, cross-team visibility."},
            {"signal_name": "Follow-up Requested", "detected": True,
             "details": "Vikram agreed to set up call with CTO next week."},
            {"signal_name": "Pricing Asked", "detected": True,
             "details": "Asked about pricing and expressed budget constraints."},
            {"signal_name": "Objections Raised", "detected": True,
             "details": "Budget threshold (50K/year) and need for CTO approval."},
        ],
        "persona": {
            "type": "Evaluator",
            "budget_score": 5.0,
            "authority_score": 3.0,
            "need_score": 8.0,
            "timeline_score": 4.0,
            "discovery_insights": [
                "IT Manager at mid-size company (150 employees)",
                "40 active project management users",
                "Current tools: Jira + Google Sheets",
                "Non-technical teams struggle with Jira complexity",
                "CTO Anand is decision maker, on vacation till Monday",
            ],
        },
        "action_items": [
            {"description": "Prepare ROI business case document with migration timeline",
             "category": "send_info", "urgency": "immediate"},
            {"description": "Set up free trial workspace for Vikram's team",
             "category": "follow_up", "urgency": "immediate"},
            {"description": "Send calendar options for Tuesday/Wednesday call with CTO Anand",
             "category": "follow_up", "urgency": "this_week"},
            {"description": "Follow up if no response by Wednesday on CTO meeting",
             "category": "follow_up", "urgency": "next_week"},
        ],
        "path_to_conversion": "Key blocker is CTO approval. Prepare a compelling business case showing ROI over current Jira + Sheets setup. Get trial feedback from the team before the CTO meeting. During CTO call, focus on security, compliance, and cost savings rather than features.",
        "rebuttals": [
            "For budget concern: Annual billing saves 20%, bringing per-user cost to just Rs 320/month. Calculate wasted hours on current fragmented tooling.",
            "For authority gap: Offer to join the CTO call directly to address technical and security concerns.",
        ],
        "key_data_points": {
            "company_size": "150 employees",
            "active_users": "40",
            "current_tools": "Jira + Google Sheets",
            "budget_threshold": "50K/year (CTO approval needed above)",
            "decision_maker": "CTO Anand",
            "annual_cost": "1.54L (with annual discount)",
        },
        "follow_up_urgency": "this_week",
        "call_summary": "SaaS demo with IT Manager Vikram. Strong need identified (Jira too complex for non-tech teams) but authority gap — CTO Anand must approve. Trial being set up, business case document to be prepared. Follow-up meeting with CTO planned for next week.",
    }


def _cold_lead_analysis() -> Dict[str, Any]:
    """Cold Call Cold Lead — low scores, minimal engagement."""
    return {
        "quality_scores": [
            {"parameter_name": "Opening & Greeting", "score": 5.0,
             "justification": "Basic cold call opening. Did not establish rapport before pitching."},
            {"parameter_name": "Need Discovery", "score": 3.0,
             "justification": "Minimal discovery. Did not explore customer's current situation before pitching."},
            {"parameter_name": "Product Knowledge", "score": 6.0,
             "justification": "Mentioned key features but could not demonstrate value due to short call."},
            {"parameter_name": "Objection Handling", "score": 4.0,
             "justification": "Attempted to pivot to health insurance after term insurance rejection, but poorly timed."},
            {"parameter_name": "Pricing Discussion", "score": 2.0,
             "justification": "No pricing discussion occurred. Customer shut down before reaching this stage."},
            {"parameter_name": "Urgency Creation", "score": 2.0,
             "justification": "No urgency created. Customer was not engaged enough for urgency tactics."},
            {"parameter_name": "Next Steps", "score": 4.0,
             "justification": "Managed to get email for follow-up, but weak commitment."},
            {"parameter_name": "Call Control", "score": 3.0,
             "justification": "Customer controlled the entire call. Agent was reactive, not proactive."},
            {"parameter_name": "Active Listening", "score": 5.0,
             "justification": "Acknowledged customer's existing coverage and time constraints."},
            {"parameter_name": "Closing Technique", "score": 3.0,
             "justification": "Only managed to close for email permission, not a meaningful next step."},
        ],
        "overall_score": 37.0,
        "lead_intent_score": 15.0,
        "intent_classification": "cold",
        "intent_signals": [
            {"signal_name": "Budget Mentioned", "detected": False,
             "details": "No budget discussion occurred."},
            {"signal_name": "Timeline Discussed", "detected": False,
             "details": "No timeline discussed."},
            {"signal_name": "Decision Maker Identified", "detected": False,
             "details": "Unknown if customer is sole decision maker for insurance."},
            {"signal_name": "Competitor Comparison", "detected": True,
             "details": "Customer mentioned existing coverage with HDFC Life."},
            {"signal_name": "Specific Requirements Stated", "detected": False,
             "details": "No requirements discussed — customer not interested."},
            {"signal_name": "Follow-up Requested", "detected": False,
             "details": "Email permission was reluctantly given, not a genuine follow-up request."},
            {"signal_name": "Pricing Asked", "detected": False,
             "details": "Customer did not ask about pricing."},
            {"signal_name": "Objections Raised", "detected": True,
             "details": "Already has insurance with HDFC Life. Too busy. Not interested."},
        ],
        "persona": {
            "type": "Not Interested",
            "budget_score": 1.0,
            "authority_score": 2.0,
            "need_score": 1.0,
            "timeline_score": 0.0,
            "discovery_insights": [
                "Existing HDFC Life insurance customer",
                "Recently reviewed coverage with financial advisor",
                "Busy professional with limited time",
                "Email: kiran@techworks.com",
            ],
        },
        "action_items": [
            {"description": "Send one-page plan summary email to kiran@techworks.com",
             "category": "send_info", "urgency": "this_week"},
            {"description": "Add to nurture sequence for follow-up in 6 months",
             "category": "follow_up", "urgency": "nurture"},
        ],
        "path_to_conversion": "Very low conversion probability in near term. Customer is satisfied with existing HDFC Life coverage. Best approach is to send the email as promised and add to long-term nurture. Re-engage in 6 months or when policy renewal approaches.",
        "rebuttals": [
            "For 'already have insurance': Many professionals find they are underinsured when life circumstances change. Our comparison tool can show coverage gaps without obligation.",
        ],
        "key_data_points": {
            "existing_insurance": "HDFC Life",
            "recent_review": "Last month with financial advisor",
            "email": "kiran@techworks.com",
        },
        "follow_up_urgency": "nurture",
        "call_summary": "Cold call to busy professional Kiran who is not interested in new insurance. Already has HDFC Life coverage reviewed last month. Managed to get email permission for follow-up material. Very low conversion probability — nurture lead only.",
    }


def _hinglish_analysis() -> Dict[str, Any]:
    """Hinglish Real Estate — moderate-high scores, mixed language."""
    return {
        "quality_scores": [
            {"parameter_name": "Opening & Greeting", "score": 7.5,
             "justification": "Good opening with reference to customer's inquiry. Natural Hinglish rapport."},
            {"parameter_name": "Need Discovery", "score": 7.0,
             "justification": "Identified budget range and unit preference. Could have explored lifestyle needs more."},
            {"parameter_name": "Product Knowledge", "score": 8.5,
             "justification": "Detailed knowledge of available units, pricing, floor plans, and loan options."},
            {"parameter_name": "Objection Handling", "score": 7.5,
             "justification": "Handled budget objection by offering park-facing alternative within range."},
            {"parameter_name": "Pricing Discussion", "score": 8.0,
             "justification": "Clear pricing for multiple options. Mentioned bank loan rates and limited time discount."},
            {"parameter_name": "Urgency Creation", "score": 8.0,
             "justification": "Mentioned limited time discount of 2 lakhs before March 15th deadline."},
            {"parameter_name": "Next Steps", "score": 8.5,
             "justification": "Site visit booked for Saturday 11 AM. WhatsApp materials to be sent."},
            {"parameter_name": "Call Control", "score": 7.0,
             "justification": "Good flow but could have probed deeper before jumping to solutions."},
            {"parameter_name": "Active Listening", "score": 7.5,
             "justification": "Understood budget constraints and offered suitable alternative immediately."},
            {"parameter_name": "Closing Technique", "score": 7.5,
             "justification": "Site visit scheduled but no booking commitment. Discount urgency was good."},
        ],
        "overall_score": 77.0,
        "lead_intent_score": 72.0,
        "intent_classification": "hot",
        "intent_signals": [
            {"signal_name": "Budget Mentioned", "detected": True,
             "details": "Budget around 70 lakhs. Interested in 72 lakh unit."},
            {"signal_name": "Timeline Discussed", "detected": True,
             "details": "Site visit Saturday. Needs to discuss with husband (back Thursday)."},
            {"signal_name": "Decision Maker Identified", "detected": True,
             "details": "Husband is co-decision maker, out of town till Thursday."},
            {"signal_name": "Competitor Comparison", "detected": False,
             "details": "No competitor properties mentioned."},
            {"signal_name": "Specific Requirements Stated", "detected": True,
             "details": "3 BHK, park-facing acceptable, covered parking needed, loan financing 80%."},
            {"signal_name": "Follow-up Requested", "detected": True,
             "details": "Customer requested site visit on Saturday and floor plans on WhatsApp."},
            {"signal_name": "Pricing Asked", "detected": True,
             "details": "Asked about pricing and loan financing options."},
            {"signal_name": "Objections Raised", "detected": True,
             "details": "Budget constraint — 85L too high, prefers 70L range."},
        ],
        "persona": {
            "type": "Interested Buyer",
            "budget_score": 7.0,
            "authority_score": 6.0,
            "need_score": 8.0,
            "timeline_score": 7.0,
            "discovery_insights": [
                "Looking for 3 BHK in Prestige Lakeside",
                "Budget: around 70 lakhs",
                "Needs 80% loan financing",
                "Co-decision maker: husband (available Thursday)",
                "Interested in 8th floor park-facing unit at 72L",
            ],
        },
        "action_items": [
            {"description": "Send floor plan, brochure, and price breakup via WhatsApp",
             "category": "send_info", "urgency": "immediate"},
            {"description": "Confirm Saturday 11 AM site visit",
             "category": "site_visit", "urgency": "immediate"},
            {"description": "Prepare loan pre-approval options with SBI rate details",
             "category": "follow_up", "urgency": "this_week"},
            {"description": "Follow up after site visit for booking decision before March 15 discount deadline",
             "category": "follow_up", "urgency": "this_week"},
        ],
        "path_to_conversion": "Customer is interested in 8th floor park-facing unit at 72L. Husband is co-decision maker — ensure both attend site visit. Emphasize the 2L discount deadline (March 15) during visit. Have loan advisor available at site for immediate pre-approval.",
        "rebuttals": [
            "For price concern: Park-facing unit at 72L includes covered parking (usually 3-5L extra). Plus 2L discount before March 15 makes effective price 70L.",
        ],
        "key_data_points": {
            "property": "Prestige Lakeside",
            "unit_type": "3 BHK, 8th floor, park-facing",
            "price": "72 lakhs",
            "loan_requirement": "80% financing",
            "preferred_bank": "SBI at 8.5%",
            "site_visit": "Saturday 11 AM",
            "discount_deadline": "March 15 — 2L off",
        },
        "follow_up_urgency": "immediate",
        "call_summary": "Hinglish call about 3 BHK in Prestige Lakeside. Customer Meera interested in 8th floor park-facing unit at 72L (within 70L budget after 2L discount). Needs 80% loan. Site visit scheduled Saturday 11 AM with husband. Good conversion potential if discount urgency maintained.",
    }


# ── Public helpers ──────────────────────────────────────────────────────────

HOT_LEAD_ANALYSIS = _hot_lead_analysis()
WARM_LEAD_ANALYSIS = _warm_lead_analysis()
COLD_LEAD_ANALYSIS = _cold_lead_analysis()
HINGLISH_ANALYSIS = _hinglish_analysis()


def analysis_as_json(analysis_dict: Dict[str, Any]) -> str:
    """Return the analysis dict as a JSON string (simulates LLM output)."""
    return json.dumps(analysis_dict)


def analysis_with_code_fences(analysis_dict: Dict[str, Any]) -> str:
    """Return the analysis dict wrapped in markdown code fences."""
    return f"```json\n{json.dumps(analysis_dict, indent=2)}\n```"
