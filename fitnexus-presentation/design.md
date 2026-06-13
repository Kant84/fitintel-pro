# FitNexus AI Presentation — Visual Design Document

## 1. Profile Baseline Declaration

- **Profile selection**: `profiles/strategic.md`
- **Selection rationale**: FitNexus AI — это техническая платформа с бизнес-целями (Fitness OS). Презентация должна демонстрировать архитектурную зрелость, масштабируемость и продуктовую ценность. Аудитория: технические специалисты, инвесторы, потенциальные клиенты (владельцы фитнес-клубов).
- **Referenced dimensions**: Information density (medium-high), narrative style (persuasion-driven), color guidance (steady + premium), font hierarchy, content expression techniques (roadmap, architecture diagrams, big numbers).
- **Deviation notes**: Добавлен tech-элемент в стиль (ближе к продуктовым презентациям Apple/Notion), так как продукт — технологическая платформа. Цветовая схема отклоняется от классического navy в сторону dark graphite + teal (здоровье) + orange (энергия фитнеса).

## 2. Style Baseline Declaration

- **Style anchor selection**:
  1. **Apple Keynote (product launches)**: Чистый минимализм, крупные типографские акценты, градиентные маски на изображениях, фокус на одной идее на слайд. Отсюда берём: макеты cover/chapter, работу с изображениями, иерархию текста.
  2. **McKinsey/BCG strategic reports**: Структурированность, данные в центре, чёткая аргументация, roadmap-визуализации. Отсюда берём: layout content-страниц, таблицы, диаграммы, плотность информации.
  3. **Notion/Linear (SaaS products)**: Dark UI aesthetic, современный tech-вайб, функциональная красота. Отсюда берём: тёмную тему, цветовую палитру, современный tech-фон.
- **Referenced dimension explanation**: Apple — визуальный импакт и типографика; McKinsey — структура и подача данных; Notion/Linear — цветовая схема и общий tech-стиль.

## 3. Style Details

### 3.1 Color Design Principles

- **Color tendency**: In between — stability as foundation с локальными яркими акцентами (оранжевый для фитнес-энергии).
- **Temperature**: Cool foundation (графит, teal) + warm accent (оранжевый) — контраст "технологии + энергия".
- **Primary**: `#0D9488` (teal-600) — здоровье, технологии, свежесть. Не банальный синий, но tech.
- **Background**: `#0B1220` (dark graphite) — премиальный тёмный фон, современный SaaS look.
- **Surface**: `#151E2E` (slightly lighter graphite) — для карточек, таблиц, контейнеров.
- **Text**: `#F1F5F9` (slate-100) — основной светлый текст на тёмном.
- **Secondary text**: `#94A3B8` (slate-400) — вторичный текст, аннотации.
- **Accent**: `#F97316` (orange-500) — энергия фитнеса, ключевые цифры, CTA. Использовать сдержанно.
- **Border/Divider**: `#1E293B` (slate-800) — тонкие границы.
- **Success**: `#10B981` (emerald-500) — для статусов ✅, успешных метрик.
- **Warning/Progress**: `#FBBF24` (amber-400) — для статусов 🔄, в процессе.

### 3.2 Font Usage Principles

- **Title font**: "Liter" — современный neo-grotesque, tech-оптимизированный. Использовать Bold, ALL CAPS с увеличенным letter spacing для главных заголовков.
- **Body font**: "QuattrocentoSans" — классический sans-serif, отличная читаемость на экране.
- **Number font**: "Liter" Bold — крупные цифры (KPI, метрики).
- **Font size hierarchy**:
  - Cover title: 48–52px
  - Page title: 28–32px
  - Subtitle / section header: 22–24px
  - Body text: 18–20px (не ниже 18px)
  - Big numbers (KPI): 48–60px
  - Annotations / source: 13–14px
  - Badge/label: 12–13px uppercase

### 3.3 Text Box and Container Styles

- **Content separation**: Приоритет — whitespace + font size hierarchy. Карточки использовать для группировки связанных элементов.
- **Cards**: Sharp corners (0px radius) или микро-скругление 2px. Border: 1px solid `#1E293B`. Fill: `#151E2E`. Нет теней — flat dark design.
- **Decorative elements**: Тонкие горизонтальные линии (1px, `#1E293B`) для разделения секций. Вертикальные цветные полоски (3-4px wide, primary/accent) как маркеры секций.

### 3.4 Image Style

- **Icons**: Solid icons (Font Awesome `fas:`), цвет primary или accent, размер 24–32px. Использовать для маркировки модулей и фич.
- **Tables**: Minimal dark style — header с primary fill, body с alternating surface/background, тонкие границы. Без ярких цветов в данных строках.
- **Charts**: Minimal dark style — series colors: primary (teal), accent (orange), secondary (slate). Grid lines: `#1E293B`. Нет фона у чартов (transparent).
- **Illustrations**: High-quality tech/fitness imagery для cover/chapter pages. Градиентная маска (dark graphite → transparent) для текстового overlay. Стиль: cinematic, dark moody lighting.

## 4. Layout System

### 4.1 Global Layout Characteristics

- **Canvas**: 1280 x 720px (16:9)
- **Page margins**: 60px left/right, 50px top, 40px bottom
- **Unified elements across all content pages**:
  - Top-left: FitNexus AI logo text (badge-style, primary color, 12px uppercase, letter spacing 2px) at [60, 24]
  - Bottom-right: page number (14px, secondary text color) at [1180, 690]
  - Bottom-left: thin accent line (40px wide, 3px tall) at [60, 690]
- **Grid**: All content aligned to 60px left margin, 1220px right edge (content width 1160px)

### 4.2 Special Page Layouts

- **Cover page (Hero design)**: Full-bleed background image (dark tech/fitness) + градиентная маска (graphite, opacity 0.85). Title: large centered, 48-52px, white. Subtitle: 22px, secondary text. Badge с версией и датой.
- **Table of contents (Grid layout)**: 6 chapter cards в 2x3 или 3x2 grid. Each card: icon + chapter number + title. Surface fill, hover-like border highlight.
- **Chapter pages (Hero design)**: Background image с сильной градиентной маской. Large chapter number (60-72px, accent color, low opacity) + chapter title (36-40px, white) + subtitle (18px).
- **Final page**: Similar to cover — full-bleed image + маска + centered closing message.

### 4.3 Content Page Layout Patterns

- **Pattern A — Big numbers + interpretation**: 3-4 KPI cards в row (big number + label), ниже — развёрнутый текст/буллеты.
- **Pattern B — Left-right split**: Left 55% — текст/буллеты, Right 45% — chart/diagram/image.
- **Pattern C — Full-width table**: Title + description + full-width table.
- **Pattern D — Timeline/Roadmap**: Horizontal timeline с phase cards below.
- **Pattern E — Architecture diagram**: Visual diagram built with shapes + labels.
- **Pattern F — Multi-column cards**: 2-4 equal columns с icon + title + description.

## 5. Style Usage Rules

### TextStyles:
- `title`: Page titles (28-32px, white, Liter) — все content page headings
- `subtitle`: Subtitles, section labels (20-22px, slate-400, QuattrocentoSans)
- `body`: Body text, bullet points (18px, slate-100, QuattrocentoSans, lineHeight 1.6)
- `kpi`: Big numbers (52px, accent orange, Liter Bold)
- `kpi_label`: KPI labels (14px, slate-400, uppercase, letterSpacing 1px)
- `badge`: Small badges/tags (12px, uppercase, letterSpacing 1px)
- `caption`: Annotations, sources (13px, slate-400)

### Color allocation:
- `primary` (#0D9488): Title accents, icon fills, chart primary series, header fills, active elements
- `background` (#0B1220): Page backgrounds
- `surface` (#151E2E): Cards, table body alternate rows, containers
- `text` (#F1F5F9): Primary text
- `secondary` (#94A3B8): Secondary text, labels, captions
- `accent` (#F97316): KPI numbers, key highlights, CTA elements (used sparingly)
- `border` (#1E293B): All borders, dividers, grid lines
- `success` (#10B981): Completed status indicators
- `warning` (#FBBF24): In-progress status indicators

### TableStyle:
- `default`: Header fill primary, header text white, body alternating background/surface, body text slate-100, border 1px solid border color

## 6. Risk Prohibitions

- [ ] **No blue/cyan primary**: Даже при tech-теме — primary это teal, не синий. Запрещён cheap blue (#0A97C0, #2C80FD).
- [ ] **No rounded rectangles**: Только sharp corners (0-2px radius) — strategic rigor.
- [ ] **No gradient backgrounds on content pages**: Градиенты только на cover/chapter как image masks. Content pages: solid dark background.
- [ ] **Body font not below 18px**: Minimum 18px for body text, 13px for captions only.
- [ ] **No pure white backgrounds**: All pages dark (graphite).
- [ ] **No orange overuse**: Accent only for KPIs and key highlights — max 10% of elements.
- [ ] **No misaligned grids**: All elements align to 60px left margin. No offset layouts.
- [ ] **No decorative images on content pages**: Images only on cover/chapter/final pages.
- [ ] **No unsupported claims**: All metrics from TZ document only.

## 7. Theme Definition

```yaml
theme:
  colors:
    primary: "#0D9488"
    background: "#0B1220"
    surface: "#151E2E"
    text: "#F1F5F9"
    secondary: "#94A3B8"
    accent: "#F97316"
    border: "#1E293B"
    success: "#10B981"
    warning: "#FBBF24"
  textStyles:
    title:
      fontSize: 30
      color: "$text"
      fontFamily: "Liter"
      lineHeight: 1.2
    subtitle:
      fontSize: 20
      color: "$secondary"
      fontFamily: "QuattrocentoSans"
      lineHeight: 1.3
    body:
      fontSize: 18
      color: "$text"
      fontFamily: "QuattrocentoSans"
      lineHeight: 1.6
    kpi:
      fontSize: 52
      color: "$accent"
      fontFamily: "Liter"
      lineHeight: 1.1
    kpi_label:
      fontSize: 14
      color: "$secondary"
      fontFamily: "QuattrocentoSans"
      letterSpacing: 1
      lineHeight: 1.3
    badge:
      fontSize: 12
      color: "$primary"
      fontFamily: "Liter"
      letterSpacing: 1
      lineHeight: 1.3
    caption:
      fontSize: 13
      color: "$secondary"
      fontFamily: "QuattrocentoSans"
      lineHeight: 1.4
  tableStyles:
    default:
      fontSize: 16
      fontFamily: "QuattrocentoSans"
      headerFill: "$primary"
      headerColor: "#FFFFFF"
      headerBold: true
      bodyFill: ["$background", "$surface"]
      bodyColor: "$text"
      border:
        style: solid
        width: 1
        color: "$border"
```
