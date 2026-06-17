"""The agent's tools: `search_company` and `find_decision_makers`.

Per the assignment, the data is mock — the point is to demonstrate the agent
deciding which tool to call and integrating the results, not the realism of the
data. A handful of companies are seeded with hand-written profiles/contacts;
anything else gets a deterministic generated record so the agent always has
something plausible to reason over.
"""

from __future__ import annotations

import hashlib
from typing import Any

# OpenAI-compatible function schema advertised to Qwen. The description tells
# the model *when* to reach for the tool, which improves tool-selection.
SEARCH_COMPANY_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_company",
        "description": (
            "Look up a company to gather firmographic facts (industry, size, "
            "headquarters, products, recent signals). Call this whenever you need "
            "concrete information about the target company before writing the sales "
            "brief — do not answer from memory alone. Accepts a company name, a "
            "website/domain, or a short description."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Company name, website/domain, or short description.",
                }
            },
            "required": ["query"],
        },
    },
}


# A few seeded profiles spanning archetypes a B2B 出海 seller would meet:
# a vertical SaaS, a hardware manufacturer, and a DTC e-commerce brand.
_SEEDED: dict[str, dict[str, Any]] = {
    "northwind logistics": {
        "name": "Northwind Logistics",
        "website": "northwindlogistics.com",
        "industry": "Freight forwarding & supply-chain software",
        "size": "约 400 人",
        "headquarters": "Rotterdam, Netherlands",
        "products": ["跨境货运代理", "自研 TMS 运输管理系统"],
        "recent_signals": [
            "2025 年完成 B 轮融资，宣布拓展东南亚航线",
            "正在招聘多名 '海外市场拓展' 与 '解决方案工程师'",
        ],
        "regions": ["EU", "正在进入东南亚"],
    },
    "lumen analytics": {
        "name": "Lumen Analytics",
        "website": "lumenanalytics.io",
        "industry": "数据分析 SaaS（零售行业 BI）",
        "size": "约 80 人",
        "headquarters": "Austin, TX, USA",
        "products": ["零售销售预测平台", "门店选址分析"],
        "recent_signals": [
            "近期发布面向中小连锁的自助式分析套件",
            "官网新增多语言支持，疑似筹备海外扩张",
        ],
        "regions": ["North America"],
    },
    "aurora outdoor": {
        "name": "Aurora Outdoor",
        "website": "auroraoutdoor.com",
        "industry": "户外装备 DTC 电商品牌",
        "size": "约 150 人",
        "headquarters": "Denver, CO, USA",
        "products": ["露营与徒步装备", "DTC 订阅式会员"],
        "recent_signals": [
            "亚马逊与独立站双渠道增长，毛利承压",
            "供应链高度依赖单一亚洲代工厂",
        ],
        "regions": ["North America", "少量欧洲订单"],
    },
}


def _generated_record(query: str) -> dict[str, Any]:
    """Deterministic fallback so unknown queries still return a usable profile.

    Keyed off a hash of the query so the same input always yields the same
    record (handy for demos and for the stub path).
    """
    seed = int(hashlib.sha256(query.lower().encode()).hexdigest(), 16)
    industries = [
        "B2B SaaS（工作流自动化）",
        "工业制造 / 自动化设备",
        "金融科技（支付与风控）",
        "消费电子 / IoT 硬件",
        "医疗健康信息化",
    ]
    sizes = ["约 50 人（早期）", "约 200 人（成长期）", "约 800 人（规模化）"]
    hqs = ["San Francisco, USA", "London, UK", "Berlin, Germany", "Singapore", "Toronto, Canada"]

    cleaned = query.strip()
    looks_like_url = "." in cleaned and " " not in cleaned
    if looks_like_url:
        # Strip scheme + path + www, then turn the domain root into a name:
        # "https://acme-robotics.com/about" -> domain "acme-robotics.com",
        # name "Acme Robotics".
        domain = cleaned.split("//")[-1].split("/")[0]
        domain = domain[4:] if domain.startswith("www.") else domain
        website = domain
        name = domain.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
    else:
        name = cleaned
        website = f"{cleaned.lower().replace(' ', '')}.com"

    return {
        "name": name,
        "website": website,
        "industry": industries[seed % len(industries)],
        "size": sizes[seed % len(sizes)],
        "headquarters": hqs[seed % len(hqs)],
        "products": ["核心产品线（mock）", "配套服务（mock）"],
        "recent_signals": [
            "近 6 个月在招聘海外市场/销售岗位（mock 信号）",
            "官网与社媒近期更新频繁，处于增长阶段（mock 信号）",
        ],
        "regions": ["待验证"],
        "_note": "未命中种子库，以下为基于查询确定性生成的 mock 数据。",
    }


def _match_seed_key(query: str) -> str | None:
    """Return the seeded company key matching `query`, or None.

    Exact match first, then a loose contains-match so "northwind" finds
    "northwind logistics". Shared by both tools so they agree on identity.
    """
    key = query.strip().lower()
    if key in _SEEDED:
        return key
    for seeded_key in _SEEDED:
        if key and (key in seeded_key or seeded_key in key):
            return seeded_key
    return None


def search_company(query: str) -> dict[str, Any]:
    """Return a (mock) firmographic record for a company query."""
    seed_key = _match_seed_key(query)
    if seed_key is not None:
        return _SEEDED[seed_key]
    return _generated_record(query)


# --------------------------------------------------------------------------- #
# Tool 2: find_decision_makers — who to actually reach out to.
# --------------------------------------------------------------------------- #
FIND_DECISION_MAKERS_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "find_decision_makers",
        "description": (
            "Find likely decision-makers / key contacts at a company (name, title, "
            "LinkedIn). Call this AFTER search_company, once you know the company, to "
            "identify who a salesperson should reach out to for an overseas B2B deal."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "The company name (as resolved by search_company).",
                }
            },
            "required": ["company"],
        },
    },
}

# Seeded contacts, keyed by the same lowercase keys as _SEEDED.
_SEEDED_CONTACTS: dict[str, list[dict[str, Any]]] = {
    "northwind logistics": [
        {
            "name": "Sven de Vries",
            "title": "VP of International Expansion",
            "linkedin": "linkedin.com/in/sven-de-vries",
            "note": "负责东南亚航线拓展，出海决策的直接相关人。",
        },
        {
            "name": "Maaike Jansen",
            "title": "Head of Sales Operations",
            "linkedin": "linkedin.com/in/maaike-jansen",
            "note": "管理销售流程与工具采购。",
        },
    ],
    "lumen analytics": [
        {
            "name": "Daniel Reyes",
            "title": "Co-founder & CEO",
            "linkedin": "linkedin.com/in/daniel-reyes",
            "note": "早期公司，CEO 通常亲自决策海外扩张。",
        },
        {
            "name": "Priya Nair",
            "title": "Head of Growth",
            "linkedin": "linkedin.com/in/priya-nair",
            "note": "主导多语言上线与获客增长。",
        },
    ],
    "aurora outdoor": [
        {
            "name": "Hannah Brooks",
            "title": "Director of E-commerce",
            "linkedin": "linkedin.com/in/hannah-brooks",
            "note": "负责 DTC 与渠道增长，对获客 ROI 敏感。",
        },
        {
            "name": "Marcus Cole",
            "title": "Head of Supply Chain",
            "linkedin": "linkedin.com/in/marcus-cole",
            "note": "供应链高度集中，相关风险的关键人。",
        },
    ],
}


def _generated_contacts(company: str) -> list[dict[str, Any]]:
    """Deterministic fallback contacts for unknown companies."""
    seed = int(hashlib.sha256(company.lower().encode()).hexdigest(), 16)
    first = ["Alex", "Jordan", "Taylor", "Morgan", "Chris", "Sam"]
    last = ["Lee", "Patel", "Garcia", "Müller", "Tanaka", "Novak"]
    titles = ["VP of Sales", "Head of Growth", "Chief Revenue Officer", "Director of BD"]

    def person(i: int) -> dict[str, Any]:
        fn = first[(seed + i) % len(first)]
        ln = last[(seed + i * 3) % len(last)]
        return {
            "name": f"{fn} {ln}",
            "title": titles[(seed + i) % len(titles)],
            "linkedin": f"linkedin.com/in/{fn.lower()}-{ln.lower()}",
            "note": "基于查询确定性生成的 mock 联系人。",
        }

    return [person(0), person(1)]


def find_decision_makers(company: str) -> dict[str, Any]:
    """Return (mock) key contacts for a company."""
    seed_key = _match_seed_key(company)
    contacts = _SEEDED_CONTACTS[seed_key] if seed_key is not None else _generated_contacts(company)
    return {"company": company, "contacts": contacts}
