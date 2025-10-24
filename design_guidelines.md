# HR Employee List Page Design Guidelines

## Design Approach
**System**: Bootstrap 5 Dark Theme with Linear-inspired data density and Notion's information hierarchy. Professional enterprise application focusing on clarity, efficiency, and modern aesthetics for workforce data management.

## Typography System
- **Headers**: Inter or IBM Plex Sans (700 weight) - page titles 1.75rem, section headers 1.25rem
- **Body Content**: System font stack (400 weight) - 0.875rem for data tables, 1rem for card content
- **Data/Metrics**: Tabular figures enabled - monospace for numerical consistency
- **Labels**: 0.75rem uppercase with letter-spacing 0.05em for subtle categorization

## Layout & Spacing
**Core Spacing Units**: Bootstrap's spacing scale - primarily using 2, 3, 4, 5, 6 for consistent rhythm
- Page padding: p-4 (desktop), p-3 (mobile)
- Card padding: p-4 internally
- Section gaps: mb-4 between major sections, mb-3 for related elements
- Grid gaps: gap-3 for card grids, gap-2 for compact filter elements

## Statistical Cards Section

**Layout Structure**:
- 4-column responsive grid (col-lg-3 col-md-6 col-12)
- Cards arranged horizontally across top of page, immediately below page header
- Equal height cards with consistent internal spacing

**Card Anatomy** (each statistical card):
- Icon container: 48px circle with subtle gradient background, positioned top-left
- Primary metric: Large bold number (2.5rem) with trend indicator (↑/↓ icon + percentage in smaller text)
- Label text: Below metric, muted text with descriptive title
- Comparison text: Bottom-aligned micro-copy showing period comparison ("vs. last month")
- Subtle card shadow with hover elevation effect (translate-y slight lift)

**Metrics to Display**:
1. Total Employees - with active/inactive breakdown
2. New Hires This Month - with growth percentage
3. Departments - total count with distribution indicator
4. Average Tenure - in years with median comparison

## Advanced Filter System

**Filter Bar Layout**:
- Full-width toolbar positioned directly below statistical cards, above employee list
- Two-row layout: Primary filters (row 1), Advanced filters expandable (row 2)
- Sticky positioning when scrolling past statistical cards

**Primary Filter Row**:
- Search input (col-lg-4): Prominent search with icon prefix, placeholder "Search by name, email, department..."
- Department dropdown (col-lg-2): Multi-select with badge count indicator
- Employment status toggle (col-lg-2): Chip-style buttons (Active/Inactive/All)
- Filter button (col-auto): "Advanced Filters" with expand/collapse icon
- Right-aligned actions: Export button, Add Employee button (primary accent)

**Advanced Filters Panel** (expandable):
- Date range picker: Hire date range with preset options (Last 30 days, Last quarter, etc.)
- Role/Position multi-select: Grouped by department hierarchy
- Location filter: Office locations with multi-select
- Salary range: Dual-thumb slider with numerical inputs
- Custom fields: Dynamic filters based on company metadata
- Apply/Clear buttons at panel bottom-right

**Active Filter Display**:
- Chip-based tags below filter bar showing applied filters
- Each chip: filter name + value, with X remove icon
- "Clear All Filters" link at end of chip row

## Employee List Design

**List Container**:
- Full-width data table with alternating subtle row backgrounds for readability
- Sticky header row when scrolling
- Row hover state with elevated background for interactive feedback

**Table Columns** (left to right):
1. Checkbox (bulk selection) + Avatar thumbnail (48px circular) + Name (primary text) + Job Title (muted, smaller)
2. Department - with colored dot indicator per department
3. Email - clickable with mail icon prefix
4. Phone - formatted with country code
5. Hire Date - relative time ("2 years ago") with tooltip showing exact date
6. Status Badge - pill-shaped with icon (Active: success color, Inactive: neutral)
7. Actions Dropdown - three-dot menu (View, Edit, Deactivate, More...)

**Pagination**:
- Bottom-aligned with items-per-page selector (10, 25, 50, 100)
- Page numbers with prev/next arrows
- Total count display: "Showing 1-25 of 247 employees"

## Component Library

**Cards**: Rounded corners (8px), subtle shadow, 1px border with theme-appropriate color
**Buttons**: 
- Primary (Add Employee): Solid with accent color
- Secondary (Export, Filters): Outline style
- Icon buttons: 36px square with hover background
**Inputs**: 40px height, rounded corners (6px), clear focus states with accent border
**Badges/Pills**: Rounded-full, 24px height, padding px-3
**Dropdowns**: Attached to trigger, max-height with scroll, search input for long lists

## Images
**No hero images** - this is a functional dashboard page. Use icons for:
- Statistical card icons: Line-style icons (users, trending-up, building, calendar)
- Empty state illustration: When no employees match filters, show centered illustration with friendly message

**Dark Theme Optimization**:
- Card backgrounds: Elevated surface color (lighter than page background)
- Text hierarchy: White (primary), Gray-300 (secondary), Gray-500 (tertiary)
- Borders: Subtle Gray-700/800 for visual separation without harshness
- Accent colors: Vibrant blues/purples for CTAs, maintain WCAG AA contrast ratios
- Input fields: Slightly lighter background than cards for depth perception