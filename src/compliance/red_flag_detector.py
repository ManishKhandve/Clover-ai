import re
from typing import List, Dict


# Severity ranking for escalation logic
SEVERITY_RANK = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}

# Generic implicit authority intent phrases (fallback when explicit patterns don't match)
IMPLICIT_AUTHORITY_PHRASES = [
    r"\bshall\s+be\s+entitled\b",
    r"\bstatutory\s+(right|obligation|provision)\b",
    r"\bmandatory\s+(provision|requirement|disclosure)\b",
    r"\bshall\s+not\s+waive\b",
    r"\bas\s+per\s+(the\s+)?(act|rules|regulations)\b",
    r"\bin\s+accordance\s+with\s+(the\s+)?(act|rules)\b",
]


def _normalize_text(text: str) -> str:
    """Normalize text: lowercase and collapse whitespace."""
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text.lower()).strip()


# Deterministic, machine-readable red flag rulebook
# Each rule has: rule_id, domain, severity, reason, clause_patterns, authority_patterns
RULES: List[Dict] = [
    {
        'rule_id': 'RF-REFUND-001',
        'domain': 'refund',
        'severity': 'HIGH',
        'reason': 'Clause waives or denies statutory refund rights contrary to authority.',
        'clause_patterns': [
            r"\bno\s+refund\b",
            r"\bnon[-\s]?refundable\b",
            r"\brefund\s+shall\s+not\s+be\s+payable\b",
            r"\bbuyer\s+waives\s+refund\b",
            r"\bcancellation\s+shall\s+not\s+entitle\s+refund\b",
            r"\bforfeit(ure|ed)?\s+(of\s+)?(amount|deposit|payment)\b",
            r"\bearnest\s+money\s+(shall\s+be\s+)?forfeit\b",
            r"\bdeposit\s+(is|shall\s+be)\s+non[-\s]?refundable\b",
        ],
        'authority_patterns': [
            r"\bentitled\s+to\s+refund\b",
            r"\brefund\s+(along\s+)?with\s+interest\b",
            r"\breturn\s+(of\s+)?(the\s+)?amount\b",
            r"\bsection\s+18\b",
        ],
    },
    {
        'rule_id': 'RF-INTEREST-001',
        'domain': 'interest',
        'severity': 'HIGH',
        'reason': 'Clause removes or limits statutory interest payable to the allottee.',
        'clause_patterns': [
            r"\bno\s+interest\b",
            r"\bwithout\s+interest\b",
            r"\binterest\s+shall\s+not\s+be\s+payable\b",
            r"\binterest\s+capped\s+at\s+\d+\s*%\b",
            r"\binterest\s+(waived|excluded)\b",
            r"\bexcluding\s+interest\b",
        ],
        'authority_patterns': [
            r"\binterest\s+(shall\s+be\s+)?payable\b",
            r"\bstatutory\s+interest\b",
            r"\binterest\s+as\s+prescribed\b",
            r"\bsbi\s+(prime\s+)?lending\s+rate\b",
            r"\bsection\s+18\b",
        ],
    },
    {
        'rule_id': 'RF-POSSESSION-001',
        'domain': 'possession',
        'severity': 'HIGH',
        'reason': 'Clause gives indefinite extension or denies liability for delay in possession.',
        'clause_patterns': [
            r"\bno\s+liability\s+for\s+delay\b",
            r"\b(sole|absolute)\s+discretion\s+(to\s+)?extend\b",
            r"\btime\s+is\s+not\s+of\s+the\s+essence\b",
            r"\bindefinite\s+extension\b",
            r"\bforce\s+majeure\b.*\b(indefinite|unlimited)\b",
            r"\bpossession\s+(date\s+)?(is\s+)?(tentative|approximate|estimated)\b",
            r"\bno\s+claim\s+(for|on\s+account\s+of)\s+delay\b",
        ],
        'authority_patterns': [
            r"\bpossession\s+within\s+(the\s+)?stipulated\s+period\b",
            r"\bliability\s+for\s+delay\b",
            r"\bcompensation\s+for\s+delay\b",
            r"\btimely\s+delivery\b",
            r"\bsection\s+18\b",
        ],
    },
    {
        'rule_id': 'RF-JURISDICTION-001',
        'domain': 'jurisdiction',
        'severity': 'CRITICAL',
        'reason': 'Clause ousts statutory forum/jurisdiction or restricts recourse to authority.',
        'clause_patterns': [
            r"\bexclusive\s+jurisdiction\b",
            r"\bjurisdiction\s+of\s+\w+\s+courts?\s+only\b",
            r"\barbitration\s+(only\s+)?by\s+(the\s+)?promoter\b",
            r"\ballottee\s+waives\s+right\s+to\s+approach\b",
            r"\bshall\s+not\s+(approach|file|complain)\b",
            r"\bdisputes?\s+(shall\s+be\s+)?(subject\s+to\s+)?arbitration\s+only\b",
            r"\bcivil\s+court\s+(of\s+)?\w+\s+(shall\s+have\s+)?jurisdiction\b",
        ],
        'authority_patterns': [
            r"\bjurisdiction\s+of\s+(the\s+)?(authority|tribunal|rera|maharera)\b",
            r"\bright\s+to\s+approach\s+(the\s+)?(authority|tribunal|regulatory|rera)\b",
            r"\bmay\s+(approach|file|complain)\s+(before\s+)?(the\s+)?(authority|tribunal)\b",
            r"\brera\s+(authority|tribunal)\b",
            r"\breal\s+estate\s+regulatory\s+authority\b",
        ],
    },
    {
        'rule_id': 'RF-UNILATERAL-001',
        'domain': 'unilateral',
        'severity': 'HIGH',
        'reason': 'Clause grants unilateral discretion to promoter affecting rights/obligations.',
        'clause_patterns': [
            r"\b(sole|absolute|exclusive)\s+discretion\s+(of\s+)?(the\s+)?promoter\b",
            r"\bpromoter\s+(may|can|shall)\s+change\s+(the\s+)?(area|specifications?|price|layout)\b",
            r"\bpromoter\s+reserves\s+the\s+right\s+to\s+(cancel|modify|alter|change)\b",
            r"\bwithout\s+(prior\s+)?(written\s+)?consent\s+(of\s+)?(the\s+)?(allottee|buyer|purchaser)\b",
            r"\bunilateral(ly)?\s+(change|modify|alter|cancel)\b",
            r"\bpromoter\s+shall\s+have\s+(the\s+)?(right|liberty|freedom)\s+to\b",
        ],
        'authority_patterns': [
            r"\bshall\s+(not\s+)?alter\b",
            r"\b(prior|written)\s+consent\b",
            r"\bwith\s+consent\s+of\s+(the\s+)?(allottee|buyer)\b",
            r"\bsection\s+14\b",
        ],
    },
    {
        'rule_id': 'RF-DISCLOSURE-001',
        'domain': 'disclosures',
        'severity': 'MEDIUM',
        'reason': 'Clause denies mandatory disclosures or information to the allottee.',
        'clause_patterns': [
            r"\bno\s+obligation\s+to\s+disclose\b",
            r"\bpromoter\s+is\s+not\s+required\s+to\s+(share|provide|disclose)\b",
            r"\bdocuments?\s+(will|shall)\s+not\s+be\s+provided\b",
            r"\bconfidential\s+(and\s+)?proprietary\b.*\b(not\s+share|not\s+disclose)\b",
        ],
        'authority_patterns': [
            r"\bmandatory\s+disclosure\b",
            r"\bshall\s+disclose\b",
            r"\bprovide\s+information\b",
            r"\bsection\s+4\b",
            r"\bsection\s+11\b",
        ],
    },
    {
        'rule_id': 'RF-PAYMENT-001',
        'domain': 'payment',
        'severity': 'HIGH',
        'reason': 'Clause demands payment before execution of agreement or registration.',
        'clause_patterns': [
            r"\bpayment\s+(of\s+)?\d+\s*%\s+(before|prior\s+to)\s+(registration|agreement)\b",
            r"\badvance\s+payment\s+(exceeding|more\s+than)\s+10\s*%\b",
            r"\bdemand\s+(of\s+)?payment\s+without\s+agreement\b",
        ],
        'authority_patterns': [
            r"\bnot\s+accept\s+(more\s+than\s+)?10\s*%\b",
            r"\bafter\s+execution\s+of\s+(the\s+)?agreement\b",
            r"\bsection\s+13\b",
        ],
    },
    {
        'rule_id': 'RF-AREA-001',
        'domain': 'carpet_area',
        'severity': 'HIGH',
        'reason': 'Clause uses super built-up area instead of carpet area for pricing.',
        'clause_patterns': [
            r"\bsuper\s+built[-\s]?up\s+area\b",
            r"\bsaleable\s+area\b",
            r"\bbuilt[-\s]?up\s+area\s+(for\s+)?(pricing|calculation|rate)\b",
            r"\bprice\s+(per|based\s+on)\s+(super\s+)?built[-\s]?up\b",
        ],
        'authority_patterns': [
            r"\bcarpet\s+area\b",
            r"\bsection\s+2\s*\(\s*k\s*\)\b",
            r"\bsold\s+on\s+carpet\s+area\b",
        ],
    },
    {
        'rule_id': 'RF-SPEC-001',
        'domain': 'specifications',
        'severity': 'MEDIUM',
        'reason': 'Agreement lacks mandatory specifications required under Section 13(2).',
        'clause_patterns': [
            r"\bspecifications?\s+(are\s+)?(not\s+)?(provided|mentioned|detailed)\b",
            r"\bsubject\s+to\s+change\s+without\s+notice\b",
            r"\bas\s+per\s+(promoter|builder)['']?s?\s+(sole\s+)?discretion\b",
        ],
        'authority_patterns': [
            r"\bshall\s+specify\b",
            r"\bagreement\s+(shall|must)\s+(contain|include)\b",
            r"\bsection\s+13\s*\(\s*2\s*\)\b",
            r"\bmandatory\s+particulars\b",
        ],
    },
]


def _match_any(patterns: List[str], text: str) -> List[str]:
    """Match patterns against pre-normalized text."""
    matches = []
    for p in patterns:
        if re.search(p, text):
            matches.append(p)
    return matches


def _match_implicit_authority(text: str) -> bool:
    """Check if text contains implicit authority intent phrases."""
    for p in IMPLICIT_AUTHORITY_PHRASES:
        if re.search(p, text):
            return True
    return False


def detect_red_flags(clause_text: str, authority_chunks: List[Dict], require_authority_support: bool = False) -> List[Dict]:
    """
    Deterministic rule-based red flag detection at clause level.

    Args:
        clause_text: Text of the clause under review.
        authority_chunks: List of retrieved authority chunks, each with at least 'text' and 'filename'.
        require_authority_support: If True, only flag if authority explicitly supports. 
                                   If False (default), flag problematic clauses even without explicit authority match.

    Returns:
        List of triggered red flags:
        [{
            'rule_id': str,
            'domain': str,
            'severity': str,
            'reason': str,
            'matched_clause_patterns': List[str],
            'matched_authority_patterns': List[str],
            'authority_support': List[{
                'filename': str,
                'excerpt': str,
            }],
            'has_authority_support': bool,  # Whether explicit authority support was found
        }]
    """
    triggered: List[Dict] = []
    
    # A) Normalize clause text once (lowercase + collapse whitespace)
    clause = _normalize_text(clause_text)
    if not clause:
        return triggered

    # Pre-normalize all authority chunks once
    normalized_authority = []
    for ch in authority_chunks or []:
        atext = _normalize_text(ch.get('text') or '')
        if atext:
            normalized_authority.append({
                'text': atext,
                'filename': ch.get('filename', 'authority'),
                'original_excerpt': (ch.get('text') or '')[:240]
            })

    for rule in RULES:
        clause_hits = _match_any(rule['clause_patterns'], clause)
        if not clause_hits:
            continue

        authority_hits: List[str] = []
        support: List[Dict] = []
        
        for ach in normalized_authority:
            atext = ach['text']
            # Check explicit authority patterns first
            ah = _match_any(rule['authority_patterns'], atext)
            
            # B) Implicit authority intent fallback
            if not ah and _match_implicit_authority(atext):
                ah = ['[implicit_authority_intent]']
            
            if ah:
                authority_hits.extend(ah)
                support.append({
                    'filename': ach['filename'],
                    'excerpt': ach['original_excerpt']
                })

        has_authority_support = len(support) > 0
        
        # Flag the clause if:
        # - We have explicit authority support, OR
        # - require_authority_support is False (flag based on clause pattern alone)
        if has_authority_support or not require_authority_support:
            # C) Severity escalation: jurisdiction violations are ALWAYS CRITICAL
            severity = rule['severity']
            if rule['domain'] == 'jurisdiction' and SEVERITY_RANK.get(severity, 0) < SEVERITY_RANK['CRITICAL']:
                severity = 'CRITICAL'
            
            # If no authority support, add a note and potentially lower severity
            reason = rule['reason']
            if not has_authority_support:
                reason = f"{rule['reason']} (Note: No explicit MahaRERA regulation match in retrieved docs - verify manually)"
                # Lower severity by one level if no authority support
                if severity == 'CRITICAL':
                    severity = 'HIGH'
                elif severity == 'HIGH':
                    severity = 'MEDIUM'
            
            triggered.append({
                'rule_id': rule['rule_id'],
                'domain': rule['domain'],
                'severity': severity,
                'reason': reason,
                'matched_clause_patterns': clause_hits,
                'matched_authority_patterns': list(set(authority_hits)) if authority_hits else ['[clause_pattern_only]'],
                'authority_support': support,
                'has_authority_support': has_authority_support,
            })
            
            # D) Early-exit: if CRITICAL detected with authority support, return immediately
            if severity == 'CRITICAL' and has_authority_support:
                return triggered

    return triggered

# =============================================================================
# COMPLIANCE VERIFICATION RULES
# These check for REQUIRED clauses that MUST be present in a compliant agreement
# =============================================================================

COMPLIANCE_RULES: List[Dict] = [
    {
        'rule_id': 'CMP-RERA-REG-001',
        'domain': 'registration',
        'importance': 'CRITICAL',
        'description': 'Agreement must mention RERA/MahaRERA registration number',
        'required_patterns': [
            r"\brera\s*(registration)?\s*(no|number|#)?\s*[:\-]?\s*[A-Z0-9]+",
            r"\bmaharera\s*(registration)?\s*(no|number|#)?\s*[:\-]?\s*[A-Z0-9]+",
            r"\bregistration\s*(no|number)\s*[:\-]?\s*P\d+",
            r"\bproject\s+registration\s+(number|no)",
        ],
    },
    {
        'rule_id': 'CMP-CARPET-001',
        'domain': 'carpet_area',
        'importance': 'HIGH',
        'description': 'Agreement must clearly specify carpet area in sq. ft./sq. m.',
        'required_patterns': [
            r"\bcarpet\s+area\s*[:\-]?\s*\d+",
            r"\bcarpet\s+area\s+of\s+\d+",
            r"\bcarpet\s+area\s+(is|shall\s+be)\s+\d+",
            r"\b\d+\s*(sq\.?\s*ft|sq\.?\s*m|square\s*(feet|meters?))\s*(carpet|built[\-\s]?up)?",
        ],
    },
    {
        'rule_id': 'CMP-POSSESSION-001',
        'domain': 'possession',
        'importance': 'HIGH',
        'description': 'Agreement must specify possession date or timeline',
        'required_patterns': [
            r"\bpossession\s+(date|on|by|within)",
            r"\bhandover\s+(date|by|within)",
            r"\bdelivery\s+(of\s+possession|date)",
            r"\bpossession\s+shall\s+be\s+(given|handed|delivered)",
            r"\b(proposed|expected|tentative)\s+date\s+of\s+(completion|possession)",
        ],
    },
    {
        'rule_id': 'CMP-PAYMENT-001',
        'domain': 'payment',
        'importance': 'HIGH',
        'description': 'Agreement must include payment schedule linked to construction',
        'required_patterns': [
            r"\bpayment\s+schedule\b",
            r"\binstall?ment\s+(plan|schedule)\b",
            r"\bpayment\s+linked\s+to\s+(construction|progress)",
            r"\bstage[-\s]?wise\s+payment",
            r"\bmilestone[-\s]?based\s+payment",
            r"\bconstruction[-\s]?linked\s+payment",
        ],
    },
    {
        'rule_id': 'CMP-PENALTY-001',
        'domain': 'penalty',
        'importance': 'MEDIUM',
        'description': 'Agreement should specify penalty/compensation for delays',
        'required_patterns': [
            r"\bpenalty\s+for\s+delay\b",
            r"\bcompensation\s+for\s+delay\b",
            r"\binterest\s+for\s+delay\b",
            r"\bdelay\s+(compensation|penalty|interest)",
            r"\bliable\s+to\s+pay\s+(interest|compensation|penalty)",
        ],
    },
    {
        'rule_id': 'CMP-SPECIFICATION-001',
        'domain': 'specifications',
        'importance': 'MEDIUM',
        'description': 'Agreement should include specifications and amenities details',
        'required_patterns': [
            r"\bspecifications\s+(and\s+)?(amenities|fittings|fixtures)",
            r"\bschedule\s+of\s+specifications\b",
            r"\bannexure.{0,20}specifications\b",
            r"\bfittings\s+and\s+fixtures\b",
            r"\b(internal|external)\s+specifications\b",
        ],
    },
    {
        'rule_id': 'CMP-TITLE-001',
        'domain': 'title',
        'importance': 'HIGH',
        'description': 'Agreement must contain title/ownership declaration',
        'required_patterns': [
            r"\bclear\s+(and\s+)?marketable\s+title\b",
            r"\btitle\s+(is\s+)?clear\s+and\s+free\b",
            r"\bfree\s+from\s+(all\s+)?encumbrances?\b",
            r"\btitle\s+deed\b",
            r"\bownership\s+(rights?|title)\b",
            r"\bno\s+encumbrance\b",
        ],
    },
    {
        'rule_id': 'CMP-COMMON-AREA-001',
        'domain': 'common_areas',
        'importance': 'MEDIUM',
        'description': 'Agreement should define common areas and facilities',
        'required_patterns': [
            r"\bcommon\s+areas?\s+(and\s+)?facilities\b",
            r"\bshared\s+(amenities|facilities)\b",
            r"\bundivided\s+(share|interest)\b",
            r"\bproportionate\s+share\b",
            r"\bcommon\s+area\s+maintenance\b",
        ],
    },
    {
        'rule_id': 'CMP-CANCELLATION-001',
        'domain': 'cancellation',
        'importance': 'HIGH',
        'description': 'Agreement must include cancellation/withdrawal clause',
        'required_patterns': [
            r"\bcancellation\s+(policy|clause|terms)\b",
            r"\bwithdrawal\s+(by\s+)?(allottee|buyer|purchaser)\b",
            r"\btermination\s+of\s+(agreement|contract)\b",
            r"\bright\s+to\s+(cancel|withdraw|terminate)\b",
            r"\brefund\s+on\s+cancellation\b",
        ],
    },
    {
        'rule_id': 'CMP-DISPUTE-001',
        'domain': 'dispute_resolution',
        'importance': 'MEDIUM',
        'description': 'Agreement should include dispute resolution mechanism',
        'required_patterns': [
            r"\bdispute\s+resolution\b",
            r"\barbitration\s+(clause|proceedings)\b",
            r"\brera\s+(authority|adjudicating)\b",
            r"\bappellate\s+tribunal\b",
            r"\bgrievance\s+redressal\b",
        ],
    },
]


def check_compliance(full_document_text: str) -> List[Dict]:
    """
    Check if document contains required clauses for MahaRERA compliance.
    
    Args:
        full_document_text: The complete text of the user document
        
    Returns:
        List of compliance check results:
        [{
            'rule_id': str,
            'domain': str,
            'importance': str,
            'description': str,
            'status': 'COMPLIANT' | 'MISSING',
            'matched_pattern': str or None,
        }]
    """
    results = []
    text = _normalize_text(full_document_text)
    
    if not text:
        return results
    
    for rule in COMPLIANCE_RULES:
        matched = False
        matched_pattern = None
        
        for pattern in rule['required_patterns']:
            if re.search(pattern, text):
                matched = True
                matched_pattern = pattern
                break
        
        results.append({
            'rule_id': rule['rule_id'],
            'domain': rule['domain'],
            'importance': rule['importance'],
            'description': rule['description'],
            'status': 'COMPLIANT' if matched else 'MISSING',
            'matched_pattern': matched_pattern,
        })
    
    return results


def get_compliance_summary(compliance_results: List[Dict]) -> Dict:
    """
    Generate a summary of compliance check results.
    
    Returns:
        {
            'total_checks': int,
            'compliant_count': int,
            'missing_count': int,
            'critical_missing': List[Dict],
            'high_missing': List[Dict],
            'medium_missing': List[Dict],
            'is_compliant': bool,  # True if no CRITICAL or HIGH items are missing
        }
    """
    compliant = [r for r in compliance_results if r['status'] == 'COMPLIANT']
    missing = [r for r in compliance_results if r['status'] == 'MISSING']
    
    critical_missing = [r for r in missing if r['importance'] == 'CRITICAL']
    high_missing = [r for r in missing if r['importance'] == 'HIGH']
    medium_missing = [r for r in missing if r['importance'] == 'MEDIUM']
    
    return {
        'total_checks': len(compliance_results),
        'compliant_count': len(compliant),
        'missing_count': len(missing),
        'critical_missing': critical_missing,
        'high_missing': high_missing,
        'medium_missing': medium_missing,
        'is_compliant': len(critical_missing) == 0 and len(high_missing) == 0,
    }