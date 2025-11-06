# Glossary

## UBL Release Process Terminology

### Release Stages (In Chronological Order)

#### PRD - Public Review Draft
**Example:** `prd-UBL-2.0`, `prd2-UBL-2.1`

Early stage release for public review and comment. Multiple rounds (prd, prd2, prd3) indicate revisions based on feedback.

**Characteristics:**
- Pre-standardization
- Open for public comment
- Subject to significant changes
- Not recommended for production use

---

#### CSPRD - Committee Specification Public Review Draft
**Example:** `csprd01-UBL-2.2`, `csprd02-UBL-2.3`

Public review draft at committee specification stage. More mature than PRD.

**Naming Convention:** Zero-padded numbers (csprd01, csprd02)

**Characteristics:**
- Committee-approved draft
- Public review period
- More stable than PRD
- May have multiple iterations

---

#### CSD - Committee Specification Draft
**Example:** `csd4-UBL-2.1`, `csd01-UBL-2.4`, `csd03-UBL-2.3`

Draft at committee specification level, may or may not be public review.

**Naming Variations:**
- Early: `csd4` (number without zero-padding)
- Later: `csd01` (zero-padded)

**Characteristics:**
- Working draft within committee
- May or may not be public
- Preparing for CS stage

---

#### CS - Committee Specification
**Example:** `cs-UBL-2.0`, `cs1-UBL-2.1`, `cs01-UBL-2.2`

Approved by OASIS technical committee but not yet promoted to standard.

**Naming Variations:**
- `cs` - Single committee spec
- `cs1` - Committee Specification 1
- `cs01` - Committee Specification 01 (zero-padded)

**Characteristics:**
- Committee-approved
- Stable for implementation
- May have multiple versions before standardization
- Suitable for production use with caveats

---

#### COS - Candidate OASIS Standard
**Example:** `cos1-UBL-2.1`, `cos01-UBL-2.2`

Final stage before becoming official OASIS Standard.

**Alternative Name:** "Committee OASIS Specification"

**Characteristics:**
- Approved by technical committee
- Pending final OASIS board approval
- Very stable
- Recommended for implementation

---

#### OS - OASIS Standard
**Example:** `os-UBL-2.0`, `os-UBL-2.1`, `os-UBL-2.2`, `os-UBL-2.3`, `os-UBL-2.4`

Official OASIS Standard - the final, approved release.

**Characteristics:**
- Fully approved by OASIS
- Official standard
- Production-ready
- Long-term stable
- **These get major version tags** (`v2.0`, `v2.1`, etc.)

---

### Special Release Types

#### Errata
**Example:** `errata-UBL-2.0`

Corrections and bug fixes to published standard.

**Characteristics:**
- Fixes errors in published standard
- Documentation corrections
- Schema bug fixes
- No new features

---

#### Update
**Example:** `os-UBL-2.0-update`

Updates to published standard, may include enhancements.

**Characteristics:**
- Beyond simple errata
- May include minor enhancements
- Maintains backward compatibility
- Supplements original standard

---

## UBL Technical Terminology

### XSD - XML Schema Definition
XML schema files that define UBL document structure.

**Location in releases:** `/xsd/` directory

**Key subdirectories:**
- `/xsd/maindoc/` - Main document schemas (Invoice, Order, etc.)
- `/xsd/common/` - Common component library
- `/xsd/codelist/` - Code list schemas (UBL 2.0)

---

### XSDRT - XSD Runtime
Stripped-down version of XSD schemas with annotations removed.

**Location in releases:** `/xsdrt/` directory

**Purpose:**
- Faster parsing
- Smaller file size
- Same validation rules
- Better runtime performance

---

### CL - Code Lists
Enumerated value sets used in UBL documents.

**Location in releases:** `/cl/` directory

**Examples:**
- Currency codes
- Country codes
- Unit codes
- Document types

---

### CVA - Context/Value Association
Rules for validating values based on context.

**Location in releases:** `/cva/` directory

**Introduced:** UBL 2.1

**Purpose:**
- Context-specific validation
- Business rule enforcement
- Dynamic code list validation

---

### MOD - Models
Spreadsheet models defining document assemblies.

**Location in releases:** `/mod/` directory

**Formats:**
- Excel (.xls)
- OpenDocument (.ods)

**Purpose:**
- Human-readable component definitions
- Assembly models for documents
- Data dictionary

---

### ART - Artwork
Diagrams and illustrations used in specification.

**Location in releases:** `/art/` directory

**Contents:**
- UML diagrams
- Process flows
- Architecture diagrams
- Conceptual models

---

### VAL - Validation
Validation artifacts and rules.

**Location in releases:** `/val/` directory

**Contents:**
- Schematron rules
- Validation examples
- Test suites

---

### XML - Example Instances
Sample UBL documents demonstrating usage.

**Location in releases:** `/xml/` directory

**Contents:**
- Example invoices
- Example orders
- Sample business documents
- Instance templates

---

### RNC - RELAX NG Compact
Alternative schema language (less common than XSD).

**Location in releases:** `/rnc/` directory

**Introduced:** UBL 2.1

**Purpose:**
- Alternative to XSD
- More readable syntax
- Same validation rules

---

### UML - Unified Modeling Language
UML diagrams showing conceptual models.

**Location in releases:** `/uml/` directory

**Contents:**
- Class diagrams
- Component models
- Package diagrams

---

### DB - Database
Database representations or data models.

**Location in releases:** `/db/` directory

**Contents:**
- SQL schemas
- Data models
- Entity relationships

---

## OASIS Organization Terms

### OASIS
Organization for the Advancement of Structured Information Standards

**Website:** https://www.oasis-open.org/

**Role:** Standards development organization

---

### UBL TC - Universal Business Language Technical Committee
OASIS technical committee responsible for UBL specification.

**Website:** https://www.oasis-open.org/committees/ubl/

**Role:**
- Develop UBL specifications
- Review and approve releases
- Coordinate with ISO/IEC

---

### ISO/IEC 19845
International standard for UBL.

**Relationship:**
- UBL 2.1+ are also ISO/IEC standards
- Dual-track standardization (OASIS + ISO)
- Same technical content
- Different approval processes

---

## Version Numbering

### Major.Minor Format
**Example:** `2.0`, `2.1`, `2.2`, `2.3`, `2.4`, `2.5`

**Major Version (2):**
- Significant changes
- May break backward compatibility
- UBL has only had major version 2 (after version 1)

**Minor Version (0-5):**
- Incremental enhancements
- Maintains backward compatibility
- New document types
- New components

---

### Backward Compatibility
UBL maintains backward compatibility within major version:
- UBL 2.1 documents valid in UBL 2.2
- UBL 2.2 documents valid in UBL 2.3
- UBL 2.3 documents valid in UBL 2.4

**Note:** Forward compatibility not guaranteed
- UBL 2.4 documents may use features not in 2.3

---

## Git Terminology Used in This Project

### Tag
Git reference to specific commit.

**Usage in this project:**
- `prd-UBL-2.0` - Descriptive tag for release
- `v2.0` - Major version tag for OASIS Standards only

---

### Commit
Single change set in git history.

**Usage in this project:**
- One commit per UBL release
- Separate commits for infrastructure changes
- Never mix release and infrastructure in same commit

---

### Branch
Git branch for development.

**Current branch:** `claude/ubl-release-history-plan-011CUriiTtpak7rcvp374FWT`

---

## Acronyms Quick Reference

| Acronym | Full Name | Meaning |
|---------|-----------|---------|
| UBL | Universal Business Language | XML standard for business documents |
| OASIS | Organization for the Advancement of Structured Information Standards | Standards org |
| PRD | Public Review Draft | Early draft for review |
| CSPRD | Committee Specification Public Review Draft | Committee draft for review |
| CSD | Committee Specification Draft | Committee working draft |
| CS | Committee Specification | Committee-approved spec |
| COS | Candidate OASIS Standard | Pre-standard stage |
| OS | OASIS Standard | Official standard |
| XSD | XML Schema Definition | XML schema files |
| XSDRT | XSD Runtime | Runtime-optimized schemas |
| CL | Code Lists | Enumerated value sets |
| CVA | Context/Value Association | Validation rules |
| NDR | Naming and Design Rules | Specification for creating UBL |
| ISO | International Organization for Standardization | International standards body |
| IEC | International Electrotechnical Commission | Standards body |

---

## Common Phrases

### "Standards Track Work Product"
OASIS designation for specifications intended to become standards.

### "Backward Compatible"
New version accepts documents from previous version.

### "Schema-valid"
XML document validates against XSD schema.

### "Normative"
Required part of specification (vs. informative/optional).

---

## File Naming Conventions

### Release Packages
- Format: `{stage}-UBL-{version}.zip`
- Examples: `os-UBL-2.0.zip`, `csprd01-UBL-2.2.zip`

### Specification Files
- XML: `UBL-{version}.xml`
- HTML: `UBL-{version}.html`
- PDF: `UBL-{version}.pdf`

### Manifest Files
- Format: `UBL-{version}-manifest.txt` or `{stage}-UBL-{version}-manifest.txt`
- Contents: Complete file listing with checksums

---

## Historical Context

### Why Start at UBL 2.0?
- UBL 1.0 (2004) was significantly different
- UBL 2.0 (2006) was major rewrite
- UBL 2.x series maintains consistency
- Backward compatibility within 2.x line

### Release Timeline
- **2006:** UBL 2.0 standardized
- **2013:** UBL 2.1 standardized (7 year gap)
- **2018:** UBL 2.2 standardized
- **2021:** UBL 2.3 standardized
- **2024:** UBL 2.4 standardized
- **Future:** UBL 2.5 in development

### Major Milestones
- UBL 2.1: Added CVA, RNC schemas, expanded documents
- UBL 2.2: ISO/IEC 19845 standardization
- UBL 2.3: Additional document types
- UBL 2.4: Latest official standard

---

*This glossary will be updated as needed during implementation.*
