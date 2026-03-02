"""Realistic sales call transcripts for testing.

Each transcript is a list of (speaker, start_time, end_time, text) tuples
that simulate real-world sales conversations across different scenarios.
"""

# ---------------------------------------------------------------------------
# Transcript 1: Solar Panel Installation — Hot Lead (~15 min)
# Agent: Rahul (SolarSquare), Customer: Priya Sharma (homeowner, Bangalore)
# ---------------------------------------------------------------------------

SOLAR_HOT_LEAD_SEGMENTS = [
    ("Agent", 0.0, 5.2,
     "Good morning! Thank you for calling SolarSquare. This is Rahul speaking. How can I help you today?"),
    ("Customer", 5.5, 14.8,
     "Hi Rahul, I'm Priya Sharma calling from Bangalore. I've been looking into getting solar panels installed for my house and I wanted to understand your offerings."),
    ("Agent", 15.0, 28.3,
     "Absolutely, Priya! Great to hear you're considering solar. Before I walk you through our solutions, may I ask what's prompting your interest in solar right now?"),
    ("Customer", 28.8, 48.5,
     "Well, our electricity bills have been going through the roof. Last month we paid almost twelve thousand rupees. And with summer coming, it's only going to get worse. Plus, my neighbor got solar installed and his bills dropped by almost seventy percent."),
    ("Agent", 49.0, 72.0,
     "That's a very common situation. A twelve thousand rupee monthly bill is quite significant. The good news is that with the right solar setup, we can typically reduce that by sixty to eighty percent. Can you tell me about your home? How big is your roof area, and is it a flat roof or sloped?"),
    ("Customer", 72.5, 92.0,
     "It's a flat concrete roof, around sixteen hundred square feet. We have a two-story independent house in Whitefield. I've actually already gotten a quote from Tata Solar — they quoted me around three and a half lakhs for a five kilowatt system."),
    ("Agent", 92.5, 128.0,
     "Great, so you're well-informed already. A five kilowatt system is a good starting point for your consumption level. We actually offer both five and seven kilowatt options. Given your twelve thousand monthly bill, I'd actually recommend looking at the seven kilowatt system — it would cover your full consumption plus give you buffer for summer peaks. Our five kilowatt system is priced at three lakh twenty thousand, and the seven kilowatt at four lakh ten thousand, both before the government subsidy."),
    ("Customer", 128.5, 145.0,
     "Four lakhs is a bit more than I was planning. What about the government subsidy? And does that price include installation and everything?"),
    ("Agent", 145.5, 182.0,
     "Absolutely — that's an all-inclusive price covering panels, inverter, mounting, wiring, installation, and our five-year maintenance package. Now, regarding the subsidy — the PM Surya Ghar scheme provides up to seventy-eight thousand rupees for a system up to three kilowatts and the per-kilowatt rate for above three. For your seven kilowatt system, you'd be looking at approximately ninety-four thousand in subsidy. So your effective cost comes down to about three lakh sixteen thousand."),
    ("Customer", 182.5, 198.0,
     "That's actually comparable to the Tata quote for a bigger system. What about the warranty? My concern is — what if the panels degrade quickly or there's an issue with the inverter?"),
    ("Agent", 198.5, 232.0,
     "Very valid concern, Priya. Our panels come with a twenty-five year performance warranty — guaranteed to produce at least eighty percent of their rated output at year twenty-five. The inverter has a ten-year warranty, and as I mentioned, our maintenance package covers the first five years including cleaning, monitoring, and any repairs. If anything fails in the first ten years, we replace it free of charge. We also provide a mobile app for real-time production monitoring."),
    ("Customer", 232.5, 248.0,
     "That sounds solid. One more thing — my concern is about the roof. We just got waterproofing done last year. Will the installation damage the waterproofing?"),
    ("Agent", 248.5, 278.0,
     "I completely understand that concern. Our installation uses a non-penetrating mounting system for flat roofs — the panels are secured with ballast weights and clamping systems, not bolted through your roof. So there's zero risk to your waterproofing. We actually send our structural engineer for a free site survey before installation to ensure everything is perfect. That site visit is completely free and no-obligation."),
    ("Customer", 278.5, 295.0,
     "That's reassuring. So what would be the timeline? We're hoping to get this done before May because that's when the really hot months start and our bills go even higher."),
    ("Agent", 295.5, 320.0,
     "Perfect timing. From the site survey to installation completion, we typically need about two to three weeks. If we can schedule your site visit this week, we could have you up and running by mid-March easily — well before the summer peak. The subsidy application takes a bit longer to process, about six to eight weeks, but the system would already be saving you money from day one."),
    ("Customer", 320.5, 338.0,
     "That works perfectly. I think I'd like to go ahead with the site survey. My husband and I have already discussed this and we're ready to move forward. What do I need to do?"),
    ("Agent", 338.5, 368.0,
     "Wonderful, Priya! I'll schedule a site visit for you. I have availability this Thursday and Saturday. Which would work better for you? We just need someone to be home to give our engineer roof access. He'll assess the roof, take measurements, check your electrical panel, and give you a final customized quote. There's absolutely no obligation."),
    ("Customer", 368.5, 378.0,
     "Saturday morning would be great. Around ten AM if possible."),
    ("Agent", 378.5, 402.0,
     "Saturday at ten AM — perfect. I'll block that slot right away. I'll send you a confirmation via WhatsApp along with our brochure, the detailed specification sheet, and the subsidy information document. Is this the best number to reach you?"),
    ("Customer", 402.5, 410.0,
     "Yes, this is my primary number. Please send everything to this WhatsApp."),
    ("Agent", 410.5, 430.0,
     "Done. Just to confirm — Priya Sharma, Whitefield, Bangalore, Saturday March eighth at ten AM, seven kilowatt system discussion. Is there anything else you'd like to know before we meet?"),
    ("Customer", 430.5, 440.0,
     "No, I think that covers everything. Thank you, Rahul. Looking forward to Saturday."),
    ("Agent", 440.5, 452.0,
     "Thank you, Priya! I'll make sure our best engineer visits you. Have a wonderful day, and we'll see you Saturday!"),
]

SOLAR_HOT_LEAD_RAW = "\n".join(seg[3] for seg in SOLAR_HOT_LEAD_SEGMENTS)

# ---------------------------------------------------------------------------
# Transcript 2: SaaS Demo — Warm Lead (~10 min)
# Agent: Neha (B2B SaaS sales), Customer: Vikram (IT Manager)
# ---------------------------------------------------------------------------

SAAS_WARM_LEAD_SEGMENTS = [
    ("Agent", 0.0, 8.0,
     "Hi Vikram, this is Neha from CloudDesk. Thanks for signing up for the demo. How are you doing today?"),
    ("Customer", 8.5, 16.0,
     "Hey Neha, doing well. Yeah, we've been evaluating a few project management tools and CloudDesk came up in our research."),
    ("Agent", 16.5, 32.0,
     "That's great to hear. Before I show you the platform, could you tell me a bit about your current setup? What are you using right now and what's driving the search for a new solution?"),
    ("Customer", 32.5, 58.0,
     "Sure. We're currently using a combination of Jira and Google Sheets, which is becoming a nightmare. We have about a hundred and fifty employees, maybe forty of them actively using project management tools. The main pain point is that our non-technical teams hate Jira — it's too complicated for them. We need something that works for both engineering and marketing."),
    ("Agent", 58.5, 85.0,
     "That's one of the most common scenarios we solve. CloudDesk is designed to bridge exactly that gap — it has the power Jira offers for engineering workflows but with a much simpler interface that non-technical teams actually enjoy using. Let me share my screen and walk you through the key features. Can you see my screen?"),
    ("Customer", 85.5, 88.0,
     "Yes, I can see it. Go ahead."),
    ("Agent", 88.5, 132.0,
     "Perfect. So here's the main dashboard. As you can see, you can create different workspaces for different teams. Engineering gets their sprint boards, kanban views, and backlog management. Marketing gets their campaign trackers and content calendars. But here's the key part — they can all link together. So when marketing requests a feature or a landing page from engineering, it flows seamlessly through the system. No more email chains or lost requests."),
    ("Customer", 132.5, 148.0,
     "That's interesting. The cross-team visibility is exactly what we need. What about integrations? We use Slack heavily, and obviously GitHub for version control."),
    ("Agent", 148.5, 172.0,
     "Great question. We have native integrations with Slack, GitHub, GitLab, Figma, Google Workspace, and about fifty other tools. The Slack integration is particularly popular — you get notifications, can create tasks directly from Slack messages, and even do standups through our Slack bot."),
    ("Customer", 172.5, 190.0,
     "Okay, that's solid. Now, the big question — pricing. We have budget constraints this quarter. Our CTO needs to approve anything over fifty thousand per year."),
    ("Agent", 190.5, 218.0,
     "Understood. For forty active users on our Team plan, you'd be looking at four hundred rupees per user per month, so that's sixteen thousand per month or about one lakh ninety-two thousand annually. However, we do offer annual billing at a twenty percent discount, bringing it down to about one lakh fifty-four thousand per year."),
    ("Customer", 218.5, 235.0,
     "That's over our fifty thousand threshold, so I'd need to run this by our CTO, Anand. He's the final decision maker on tool purchases. I personally think this is worth it but I can't sign off alone."),
    ("Agent", 235.5, 260.0,
     "Completely understand. Would it be helpful if I put together a business case document comparing CloudDesk against the cost of your current Jira licenses plus the productivity lost from the spreadsheet workaround? We've seen companies similar to yours save around thirty percent in project overhead after switching. I can tailor that with your specific numbers."),
    ("Customer", 260.5, 275.0,
     "Yeah, that would actually be really helpful. If you can show the ROI, Anand will be much more open to it. Can you also include the migration timeline? He'll want to know how disruptive the switch would be."),
    ("Agent", 275.5, 302.0,
     "Absolutely. Our migration from Jira typically takes two to three weeks and we provide a dedicated migration specialist at no extra cost. I'll put together the full business case with ROI projections and migration plan. When do you think you could get time with Anand to present this?"),
    ("Customer", 302.5, 318.0,
     "He's on vacation this week but should be back Monday. I could probably set up a call for next week. Maybe Tuesday or Wednesday?"),
    ("Agent", 318.5, 340.0,
     "That works perfectly. I can join the call with Anand to answer any technical questions and walk him through the security and compliance aspects, which CTOs usually want to know about. Shall I send you a few time slots for next Tuesday and Wednesday?"),
    ("Customer", 340.5, 348.0,
     "Yes, please. Send me a few options and I'll coordinate with Anand's calendar."),
    ("Agent", 348.5, 370.0,
     "Will do. In the meantime, I'll also set up a free trial workspace for your team so you can start playing around with it. That way, when Anand asks how the team feels about it, you'll have real feedback. Sound good?"),
    ("Customer", 370.5, 380.0,
     "That's a great idea. Please set that up. Thanks, Neha, this was really helpful."),
    ("Agent", 380.5, 395.0,
     "My pleasure, Vikram. I'll send over the trial invite, the business case document, and the calendar options by end of day. Have a great rest of your day!"),
]

SAAS_WARM_LEAD_RAW = "\n".join(seg[3] for seg in SAAS_WARM_LEAD_SEGMENTS)

# ---------------------------------------------------------------------------
# Transcript 3: Cold Call — Cold Lead (~5 min)
# Agent: Amit (insurance sales), Customer: Kiran (busy professional)
# ---------------------------------------------------------------------------

COLD_CALL_SEGMENTS = [
    ("Agent", 0.0, 8.0,
     "Hi, good afternoon! Am I speaking with Kiran? This is Amit calling from SecureLife Insurance."),
    ("Customer", 8.5, 12.0,
     "Yes, this is Kiran. Look, I'm in the middle of something. What is this about?"),
    ("Agent", 12.5, 28.0,
     "I understand you're busy and I'll keep this very brief. I'm calling because we have a new term insurance plan that's specifically designed for professionals like you — it offers twenty percent more coverage at the same premium as standard plans."),
    ("Customer", 28.5, 36.0,
     "I already have insurance. I'm not looking for any new plans right now. Thanks."),
    ("Agent", 36.5, 52.0,
     "I completely respect that. May I ask who you're currently insured with? Many of our clients found that they were actually underinsured when they compared their existing coverage to their actual needs. Even a quick review could—"),
    ("Customer", 52.5, 62.0,
     "I'm insured with HDFC Life and I'm perfectly happy with my coverage. I did a thorough review with my financial advisor just last month."),
    ("Agent", 62.5, 78.0,
     "HDFC Life is a great company. Since you've recently reviewed your coverage, I won't push on that. However, we also offer a health insurance add-on that many professionals find valuable — it covers critical illness with a lump sum payout that—"),
    ("Customer", 78.5, 90.0,
     "Amit, I appreciate the call, but I really don't have time for this right now. I have a meeting in five minutes. I'm not interested in any new insurance products at this time."),
    ("Agent", 90.5, 105.0,
     "I completely understand, Kiran. Could I perhaps send you a brief email with our plan details? That way you can review it at your convenience whenever you have a spare moment."),
    ("Customer", 105.5, 115.0,
     "Fine, you can send an email. But I'm not promising I'll look at it. My email is kiran at techworks dot com."),
    ("Agent", 115.5, 132.0,
     "That's perfectly fine. I'll send over a one-page summary. Kiran, thank you for your time and I apologize for catching you at a busy moment. Have a great rest of your day."),
    ("Customer", 132.5, 136.0,
     "Yeah, thanks. Bye."),
]

COLD_CALL_RAW = "\n".join(seg[3] for seg in COLD_CALL_SEGMENTS)

# ---------------------------------------------------------------------------
# Transcript 4: Hinglish Mixed Language — Real Estate (~8 min)
# Agent: Deepak, Customer: Meera (both mixing Hindi and English)
# ---------------------------------------------------------------------------

HINGLISH_SEGMENTS = [
    ("Agent", 0.0, 8.0,
     "Hello Meera ji, main Deepak bol raha hoon PropertyWala se. Aapne humari website pe inquiry ki thi Prestige Lakeside ke baare mein."),
    ("Customer", 8.5, 20.0,
     "Haan Deepak, I was looking at the three BHK options. Can you tell me about the pricing aur available units ke baare mein?"),
    ("Agent", 20.5, 45.0,
     "Of course, Meera ji. Prestige Lakeside mein three BHK apartments available hain ranging from sixty-eight lakhs to eighty-five lakhs, depending on the floor and the view. Abhi lake-facing units mein sirf do units bachi hain — woh premium pricing pe hain around eighty to eighty-five lakhs."),
    ("Customer", 45.5, 62.0,
     "Eighty-five lakhs is quite a lot. Humaara budget around seventy lakhs ke aaspaas tha. Kya koi non-lake-facing option hai jo seventy mein aa jaye?"),
    ("Agent", 62.5, 88.0,
     "Haan, definitely. Park-facing side pe do units available hain — one on the fifth floor at sixty-eight lakhs and one on the eighth floor at seventy-two lakhs. The eighth floor wala is actually a better deal because it comes with a covered parking extra and a slightly bigger balcony. Aapko site visit karna hai toh main arrange kar sakta hoon."),
    ("Customer", 88.5, 105.0,
     "The seventy-two lakhs wala sounds interesting. But loan ke baare mein — kya aapke paas tie-ups hain banks ke saath? We would need around eighty percent financing."),
    ("Agent", 105.5, 130.0,
     "Absolutely. Humara tie-up hai SBI, HDFC Bank, aur ICICI ke saath. Eighty percent financing easily mil jayega. SBI ka rate abhi sabse best chal raha hai — around eight point five percent. Pre-approved loan bhi mil sakta hai agar aapke documents ready hain. I can connect you with our loan advisor directly."),
    ("Customer", 130.5, 148.0,
     "Okay that helps. But I want to discuss with my husband first. He's out of town till Thursday. Can we do a site visit on Saturday?"),
    ("Agent", 148.5, 170.0,
     "Bilkul, Saturday works perfectly. Main Saturday morning ka slot book kar deta hoon — around eleven AM. Ek baat dhyan rakhiyega — builder is offering a limited time discount of two lakhs on bookings done before March fifteenth. So agar aapko unit pasand aata hai, toh booking jaldi karna beneficial hoga."),
    ("Customer", 170.5, 185.0,
     "Okay, that's good to know. Saturday eleven AM confirm kar lo. Aur please mujhe WhatsApp pe floor plan aur brochure bhej do."),
    ("Agent", 185.5, 205.0,
     "Done, Meera ji. Main aapko abhi WhatsApp pe eighth floor unit ka floor plan, brochure, aur price breakup bhej deta hoon. Saturday ko main aapka aur aapke husband ka wait karunga at the site office. Thank you!"),
    ("Customer", 205.5, 210.0,
     "Thank you Deepak. See you Saturday."),
]

HINGLISH_RAW = "\n".join(seg[3] for seg in HINGLISH_SEGMENTS)


def build_speaker_labeled_text(segments: list) -> str:
    """Build a [MM:SS] Speaker: text formatted transcript."""
    lines = []
    for speaker, start_time, _, text in segments:
        minutes = int(start_time // 60)
        seconds = int(start_time % 60)
        lines.append(f"[{minutes:02d}:{seconds:02d}] {speaker}: {text}")
    return "\n".join(lines)
