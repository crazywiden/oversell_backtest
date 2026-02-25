---
name: competitor-market-research
description: Use when analyzing competitors, understanding market landscape, evaluating competitive threats, preparing go-to-market strategy, or identifying differentiation opportunities for a product or business.
---

# Competitor Market Research

Systematic competitor analysis combining multiple research dimensions to produce actionable competitive intelligence. Core principle: **broad surface scanning first, deep-dive on priority targets second**.

## When to Use

**Triggers:**
- "Who are our competitors?"
- "How is the competitive landscape?"
- "What's our differentiation?"
- Preparing go-to-market strategy
- Evaluating market entry
- Identifying positioning gaps

**Not for:**
- Extracting competitor ads specifically → use `competitive-ads-extractor`
- Finding leads/customers → use `lead-research-assistant`
- Technical product comparison only

## How to Use

### Basic Research
```
Analyze the competitive landscape for [your product category].
Who are the main players and how should we differentiate?
```

### Specific Competitor Deep-Dive
```
Do a deep competitive analysis on [Competitor Name].
What are their strengths, weaknesses, and how do customers feel about them?
```

### Market Entry Analysis
```
We're entering the [market/category] space. Analyze the top 5 competitors
and identify opportunities for differentiation.
```

### Positioning Research
```
How do competitors in [category] position themselves?
What messaging angles are underutilized?
```

## Research Framework

```
PHASE 1: IDENTIFY COMPETITORS
├── Direct: same solution, same audience
├── Indirect: different solution, same problem
└── Potential: adjacent players who could enter

PHASE 2: SURFACE SCAN (all competitors)
├── Website positioning & messaging
├── Pricing model (if public)
├── Target audience signals
└── Key claimed differentiators

PHASE 3: DEEP DIVE (top 3-5 priority)
├── Business Intelligence
├── Product/Service Analysis
├── Marketing Analysis
├── Customer Perspective
├── Digital Presence
└── Strategic Analysis (SWOT)

PHASE 4: SYNTHESIZE
├── Competitive positioning map
├── SWOT for each major competitor
└── Opportunities & threats for your business
```

## Analysis Dimensions

### 1. Business Intelligence
**Questions:** Size? Funding? Revenue? Growth trajectory? Leadership?

**Sources:**
- Crunchbase, LinkedIn (company size, funding)
- Job postings (growth signals, tech stack)
- Press releases, news articles
- Glassdoor (internal culture, growth indicators)

### 2. Product/Service Analysis
**Questions:** Features? Pricing? UX quality? Unique capabilities?

**Sources:**
- Product website, feature pages
- Free trials, demos, recorded walkthroughs
- Pricing pages (screenshot and compare)
- Product review sites (G2, Capterra)

### 3. Marketing Analysis
**Questions:** Positioning? Messaging? Channels? Content strategy?

**Sources:**
- Homepage H1 and tagline (core positioning)
- Use `competitive-ads-extractor` for ad analysis
- Blog, content hub (topics, frequency)
- Social media presence and messaging

### 4. Customer Perspective
**Questions:** What do users love? Hate? Switch from/to?

**Sources:**
- G2, Capterra, TrustRadius reviews
- App store reviews (if applicable)
- Reddit, Twitter/X mentions
- "Why I switched from X" blog posts
- YouTube reviews and comparisons

**Technique:** Sort reviews by 1-2 stars for pain points, 5 stars for loved features.

### 5. Digital Presence
**Questions:** SEO strength? Social reach? Content velocity?

**Sources:**
- SimilarWeb (traffic estimates)
- Social profiles (follower counts, engagement)
- Blog posting frequency
- Backlink profile (Ahrefs, Moz)

### 6. Strategic Analysis (SWOT)
Synthesize findings into:
- **Strengths:** What they do well
- **Weaknesses:** Where they fall short
- **Opportunities:** Gaps you can exploit
- **Threats:** Where they could hurt you

## Quick Reference: Research Techniques

| Task | Technique |
|------|-----------|
| Find competitors | Search "[your category] alternatives", check G2/Capterra categories |
| Assess positioning | Read homepage H1 + subheadline, note who they say they serve |
| Find pricing | Check /pricing page, look for "Talk to sales" (means enterprise tier) |
| Customer sentiment | Sort reviews by rating, search Reddit for "[competitor] vs" |
| Growth signals | Check job postings (hiring = growing), funding news |
| Tech stack | BuiltWith, Wappalyzer, job posting requirements |

## Output Template

```markdown
# Competitive Analysis: [Market/Category]

## Executive Summary
[2-3 sentence overview of competitive landscape]

## Competitor Overview

| Competitor | Type | Positioning | Pricing | Size |
|------------|------|-------------|---------|------|
| [Name] | Direct | [1-line] | [Model] | [Est.] |

---

## Detailed Analysis

### [Competitor Name]

**Overview**
- Website: [URL]
- Founded: [Year]
- Size: [Employees, funding]
- Target: [Who they serve]

**Positioning**: [Their core promise]

**Product Strengths**
- [Strength 1]
- [Strength 2]

**Product Weaknesses**
- [Weakness 1]
- [Weakness 2]

**Customer Sentiment**
- Love: [What customers praise]
- Hate: [What customers complain about]

**SWOT Summary**
| Strengths | Weaknesses |
|-----------|------------|
| [S1] | [W1] |

| Opportunities | Threats |
|---------------|---------|
| [O1] | [T1] |

---

## Competitive Positioning Map

[Describe where each competitor sits on key dimensions]

## Key Insights

### Opportunities for Us
1. [Gap or weakness we can exploit]
2. [Underserved segment]
3. [Positioning angle not claimed]

### Threats to Monitor
1. [Competitor strength that threatens us]
2. [Market trend favoring competitor]

## Recommended Differentiation
[How to position against this competitive set]
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Only analyzing direct competitors | Include indirect + potential entrants |
| Data gathering without synthesis | Always end with SWOT + actionable insights |
| Relying only on competitor marketing | Include customer voice (reviews reveal truth) |
| One-time snapshot | Competitive landscape changes; revisit quarterly |
| Feature-only comparison | Positioning and messaging matter equally |
| Ignoring pricing strategy | Pricing reveals target market and positioning |

## Deliverable Quality Check

Before completing research, verify:
- [ ] Covered direct, indirect, and potential competitors
- [ ] Each major competitor has SWOT analysis
- [ ] Customer sentiment included (not just marketing claims)
- [ ] Clear opportunities and threats identified
- [ ] Actionable differentiation recommendations provided
- [ ] Sources documented for key claims

## Related Skills

- `competitive-ads-extractor` - For deep-dive on competitor advertising
- `lead-research-assistant` - For finding potential customers
