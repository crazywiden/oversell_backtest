---
name: startup-deep-dive
description: Use when analyzing a single startup company in depth. Triggers include researching a potential investment, evaluating acquisition target, understanding competitor strategy, due diligence on vendor/partner, or preparing for job interview at a startup.
---

# Startup Deep Dive Analysis

Comprehensive analysis of a single startup company from multiple angles. Core principle: **cross-validate claims with multiple sources; distinguish confirmed facts from estimates**.

## When to Use

**Triggers:**
- "Tell me about [startup name]"
- "Analyze [company] as an investment"
- "What do we know about [competitor]?"
- Due diligence on a vendor/partner
- Pre-interview research on a company
- Evaluating acquisition target

**Input:** Company name OR company website URL

**Not for:**
- Analyzing multiple competitors in a market → use `competitor-market-research`
- Finding leads for your product → use `lead-research-assistant`
- Extracting competitor ads → use `competitive-ads-extractor`

## Research Framework

```
PHASE 1: IDENTIFY & VERIFY
├── Confirm company name, website, LinkedIn
├── Verify it's a startup (not enterprise/SMB)
└── Note founding date and current stage

PHASE 2: COLLECT DATA (10 dimensions)
├── 1. Funding History
├── 2. Product/Service
├── 3. Company Strategy
├── 4. Company History
├── 5. Founding Team
├── 6. Revenue/ARR Estimates
├── 7. User Feedback
├── 8. Competitive Position
├── 9. Growth Trajectory
└── 10. Risk Factors

PHASE 3: ANALYZE BY PERSPECTIVE
├── Investor view
├── Customer view
├── Employee view
└── Competitor view

PHASE 4: SYNTHESIZE
├── SWOT summary
├── Key insights
└── Confidence levels on estimates
```

## 10 Analysis Dimensions

### 1. Funding History
**Questions:** Total raised? Rounds? Lead investors? Last valuation? Runway?

**Data Points:**
- Total funding amount
- Round history (Seed → Series A → B → etc.)
- Key investors (name, reputation, other portfolio)
- Last known valuation
- Last raise date (runway indicator)
- Cap table signals (down rounds, investor changes)

**Sources:** Crunchbase, PitchBook, TechCrunch, company press releases

### 2. Product/Service Offering
**Questions:** What do they sell? Who buys it? How is it priced?

**Data Points:**
- Core product(s) and features
- Pricing model and tiers (if public)
- Target customer persona
- Key differentiators claimed
- Tech stack and platform
- Integrations and ecosystem
- Patents/IP (for deep tech startups)
- Demo/free trial availability

**Sources:** Product website, pricing page, G2/Capterra feature lists, ProductHunt, USPTO (patents)

### 3. Company Strategy
**Questions:** What's their business model? Go-to-market? Moat? Market size?

**Data Points:**
- Business model (SaaS, marketplace, transactional, etc.)
- Go-to-market motion (PLG, sales-led, hybrid)
- Expansion strategy (vertical, horizontal, geographic)
- Competitive moat (network effects, data, switching costs, brand)
- Strategic partnerships or exclusives
- TAM/SAM/SOM estimates (total addressable market)
- International presence and expansion plans

**Sources:** Company website, investor presentations (if public), press interviews, job postings, industry reports

### 4. Company History
**Questions:** When founded? Any pivots? Key milestones?

**Data Points:**
- Founding date and origin story
- Pivots or major direction changes
- Key milestones (launches, major customers, expansions)
- Accelerator/incubator participation (YC, Techstars, etc.)
- Previous names or acquired companies

**Sources:** Crunchbase, LinkedIn, company About page, founder interviews

### 5. Founding Team
**Questions:** Who are the founders? What's their background? Previous exits?

**Data Points:**
- Founder names and roles
- Previous companies and exits
- Educational background
- Domain expertise
- Key executives and leadership team
- Board members
- Advisor quality

**Sources:** LinkedIn, Crunchbase, company About page, press articles

### 6. Revenue/ARR Estimates
**Questions:** What's their ARR? Growth rate? Unit economics?

**Data Points:**
- Estimated ARR (use multiple methods)
- Revenue growth rate
- Customer count (if disclosed)
- Average contract value (ACV)
- Net revenue retention (NRR) signals
- Path to profitability

**Estimation Methods:**
| Method | How |
|--------|-----|
| Employee count | $150-250K ARR per employee (SaaS) |
| Funding stage | Series A: $1-3M, B: $5-15M, C: $20-50M+ |
| Customer count × ACV | If disclosed or estimable |
| Job postings | Growth velocity indicator |
| LinkedIn employee growth | 2x employees often = 2-3x revenue |

**Important:** Always note confidence level and estimation method.

**Sources:** News articles (sometimes disclose), employee count, LinkedIn, funding announcements

### 7. User Feedback & Sentiment
**Questions:** What do users love? Hate? Why do they churn?

**Data Points:**
- Overall ratings (G2, Capterra, App Store)
- Common praise themes (5-star reviews)
- Common complaints (1-2 star reviews)
- ProductHunt launch reception
- Reddit/Twitter sentiment
- "Why I switched from X" articles
- Support quality signals

**Technique:** Sort by 1-2 stars to find real pain points; 5 stars for genuine strengths.

**Sources:** G2, Capterra, TrustRadius, ProductHunt, Reddit, Twitter/X, App Store reviews

### 8. Competitive Positioning
**Questions:** Who do they compete with? How do they differentiate?

**Data Points:**
- Direct competitors
- Indirect competitors
- Claimed differentiation
- Pricing position (premium, mid-market, value)
- Market segment focus
- Win/loss signals from reviews

**Sources:** Company website, G2 comparisons, "vs" pages, customer reviews mentioning alternatives

### 9. Growth Trajectory
**Questions:** Are they growing? How fast? Where are they heading?

**Data Points:**
- Employee count over time (LinkedIn)
- Hiring velocity and roles
- Office expansion signals
- New product launches
- Geographic expansion
- Partnership announcements
- Tech stack expansion (job postings)

**Key Indicator:** LinkedIn employee count trajectory over 6-12 months

**Sources:** LinkedIn, job postings, press releases, ProductHunt launches

### 10. Risk Factors
**Questions:** What could go wrong? Red flags?

**Data Points:**
- Founder departures or conflicts
- Down rounds or extended runway
- Glassdoor complaints (patterns)
- Customer concentration risk
- Regulatory exposure
- Technology obsolescence risk
- Market timing concerns
- Cash runway concerns
- Key person dependencies

**Sources:** Glassdoor, news articles, LinkedIn (departures), Crunchbase (funding gaps)

## Stakeholder Perspectives

Analyze findings through each lens:

| Perspective | Key Questions |
|-------------|---------------|
| **Investor** | TAM, growth rate, team quality, unit economics, exit potential |
| **Customer** | Reliability, longevity, support quality, price/value, vendor lock-in |
| **Employee** | Culture, growth opportunity, equity value, stability, learning |
| **Competitor** | Strategy, strengths to counter, weaknesses to exploit, likely moves |
| **Partner** | Reliability, alignment, growth potential, reputation |
| **Acquirer** | Strategic fit, team talent, technology, customer base, price |

## Quick Reference: Data Sources

| Source | Best For |
|--------|----------|
| **Crunchbase** | Funding, investors, team, timeline |
| **LinkedIn** | Employee count, growth, team backgrounds |
| **G2/Capterra** | User reviews, feature lists, comparisons |
| **ProductHunt** | Launch history, early adopter sentiment |
| **Glassdoor** | Employee sentiment, culture, salaries |
| **Twitter/X** | Real-time sentiment, founder voice |
| **Reddit** | Honest user feedback, complaints |
| **Company website** | Positioning, pricing, features |
| **Job postings** | Growth signals, tech stack, priorities |
| **TechCrunch/news** | Funding announcements, milestones |
| **SimilarWeb** | Traffic estimates, growth trends |
| **BuiltWith** | Technology stack detection |
| **YouTube** | Product demos, customer testimonials |
| **PitchBook** | Detailed funding and valuations (if accessible) |

## Output Template

```markdown
# Startup Deep Dive: [Company Name]

**Analyzed:** [Date]
**Website:** [URL]
**Stage:** [Seed/Series A/B/C/etc.]
**Industry:** [Industry/vertical]

---

## Executive Summary

[3-4 sentence overview: what they do, stage, key strengths, key concerns]

**Quick Stats:**
| Metric | Value | Confidence |
|--------|-------|------------|
| Founded | [Year] | Confirmed |
| Employees | [Count] | LinkedIn |
| Total Funding | $[X]M | Confirmed |
| Est. ARR | $[X]M | Estimate |
| Last Round | [Series X] at $[X]M | Confirmed |

---

## 1. Funding History

**Total Raised:** $[X]M across [N] rounds

| Round | Date | Amount | Lead Investor | Valuation |
|-------|------|--------|---------------|-----------|
| Seed | [Date] | $[X]M | [Investor] | [Val if known] |
| Series A | [Date] | $[X]M | [Investor] | [Val if known] |

**Notable Investors:** [List tier-1 investors and why notable]

**Runway Assessment:** [Last raised X months ago, estimated runway]

---

## 2. Product & Offering

**Core Product:** [What it is in 1-2 sentences]

**Key Features:**
- [Feature 1]
- [Feature 2]
- [Feature 3]

**Pricing:**
| Tier | Price | Target |
|------|-------|--------|
| [Tier] | $[X]/mo | [Who] |

**Tech Stack:** [Key technologies if known]

---

## 3. Company Strategy

**Business Model:** [SaaS/Marketplace/etc.]

**Go-to-Market:** [PLG/Sales-led/etc.]

**Target Customer:** [ICP description]

**Claimed Moat:** [What they say makes them defensible]

**Expansion Strategy:** [Where they're heading]

**Market Size (TAM/SAM):** [Estimated market size and source]

---

## 4. Company History

**Founded:** [Year] by [Founders]

**Origin:** [Brief origin story]

**Key Milestones:**
- [Year]: [Milestone]
- [Year]: [Milestone]

**Pivots:** [Any significant pivots]

---

## 5. Founding Team

### Founders

**[Name]** - [Role]
- Background: [Previous companies, education]
- Previous exits: [If any]
- LinkedIn: [URL]

### Key Executives

| Name | Role | Background |
|------|------|------------|
| [Name] | [Role] | [Brief background] |

**Board:** [Notable board members]

---

## 6. Revenue/ARR Estimates

**Estimated ARR:** $[X]M ([confidence level])

**Estimation Method:**
- [Employee count × $X per employee = $Y]
- [Or other method used]

**Growth Signals:**
- [Signal 1]
- [Signal 2]

**Unit Economics Indicators:**
- Customer count: [If known]
- Pricing tier: [Suggests ACV of $X]
- Retention signals: [Good/concerning based on reviews]

---

## 7. User Feedback

**Overall Sentiment:** [Positive/Mixed/Negative]

**G2 Rating:** [X/5] ([N] reviews)
**Capterra Rating:** [X/5] ([N] reviews)

**What Users Love:**
- [Praise theme 1]
- [Praise theme 2]

**Common Complaints:**
- [Complaint theme 1]
- [Complaint theme 2]

**Notable Quotes:**
> "[Direct quote from review]" - [Source]

---

## 8. Competitive Position

**Direct Competitors:**
| Competitor | How They Compare |
|------------|------------------|
| [Name] | [Comparison] |

**Differentiation:** [What makes them unique]

**Positioning:** [Premium/mid-market/value]

---

## 9. Growth Trajectory

**Employee Growth:**
- [X months ago]: [N] employees
- Current: [N] employees
- Growth: [X]%

**Hiring Focus:** [What roles they're hiring for]

**Expansion Signals:**
- [Signal 1]
- [Signal 2]

---

## 10. Risk Factors

**Key Risks:**
1. [Risk 1] - [Severity: High/Medium/Low]
2. [Risk 2] - [Severity]
3. [Risk 3] - [Severity]

**Red Flags Observed:**
- [If any]

**Mitigating Factors:**
- [If any]

---

## SWOT Summary

| Strengths | Weaknesses |
|-----------|------------|
| [S1] | [W1] |
| [S2] | [W2] |

| Opportunities | Threats |
|---------------|---------|
| [O1] | [T1] |
| [O2] | [T2] |

---

## Perspective Analysis

### As an Investor
[2-3 sentences on investment thesis]

### As a Customer
[2-3 sentences on customer experience/risk]

### As a Potential Employee
[2-3 sentences on employee experience]

### As a Competitor
[2-3 sentences on competitive strategy]

---

## Key Takeaways

1. [Main insight 1]
2. [Main insight 2]
3. [Main insight 3]

## Confidence Notes

| Section | Confidence | Notes |
|---------|------------|-------|
| Funding | High | Confirmed via Crunchbase |
| ARR | Low | Estimate from employee count |
| [etc.] | [Level] | [Source] |

## Sources Used
- [List all sources with URLs]
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Trusting company marketing claims | Cross-validate with reviews and third-party data |
| Missing funding history | Check Crunchbase AND TechCrunch for announcements |
| Single-source ARR estimate | Use multiple estimation methods, note confidence |
| Ignoring negative reviews | Read 1-2 star reviews - they reveal real problems |
| Overlooking team risk | Check for founder departures, key person risk |
| Not dating the analysis | Startup data changes fast - always include analysis date |
| Missing growth trajectory | LinkedIn employee count over time is key signal |
| Ignoring Glassdoor | Employee sentiment predicts many problems early |

## Quality Checklist

Before completing analysis:
- [ ] All 10 dimensions covered
- [ ] Multiple sources used per dimension
- [ ] ARR estimate includes methodology and confidence
- [ ] User feedback includes both positive AND negative
- [ ] Team backgrounds verified on LinkedIn
- [ ] Growth trajectory includes time-series data
- [ ] Risk factors explicitly identified
- [ ] SWOT completed
- [ ] Confidence levels noted for estimates
- [ ] All sources documented
- [ ] Analysis date included

## Related Skills

- `competitor-market-research` - For analyzing multiple competitors in a market
- `lead-research-assistant` - For finding potential customers
- `competitive-ads-extractor` - For analyzing competitor advertising
