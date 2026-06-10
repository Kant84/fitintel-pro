# FitIntel Pro — Product Presentation Design

## 1. Profile Baseline Declaration

- **Profile selection**: `profiles/promotion.md`
- **Selection rationale**: Это презентация продукта для потенциальных клиентов (владельцев фитнес-клубов) и инвесторов. Нужно продемонстрировать функционал, вызвать желание купить/внедрить.
- **Referenced dimensions**: Визуальный импакт, чёткая структура, бизнес-ценности, призыв к действию.
- **Deviation notes**: Более спокойная цветовая гамма для b2b-аудитории, чем обычно в promotion. Фокус на доверии и профессионализме.

## 2. Style Baseline Declaration

- **Style anchor selection**: Apple Keynote (чистота, типографика) + Stripe (b2b-tech доверие) + Yandex Cloud (русскоязычный b2b tech)
- **Referenced dimension explanation**: Apple — макеты cover и chapter, типографика; Stripe — карточки фич, чистый b2b стиль; Yandex Cloud — информационная архитектура для русскоязычного b2b

## 3. Style Details

### 3.1 Color Design Principles

- **Color tendency**: Conservative & steady — b2b продукт для владельцев бизнеса
- **Temperature**: Cool — технологичность, профессионализм
- **Primary**: `#0D9488` (teal) — здоровье, технологии
- **Background**: `#0B1220` (dark graphite) — премиальный dark-mode
- **Surface**: `#151E2E` — карточки
- **Text**: `#F1F5F9` — основной светлый
- **Secondary**: `#94A3B8` — вторичный
- **Accent**: `#F97316` (orange) — CTA, ключевые цифры
- **Success**: `#10B981` — готовые модули, статусы
- **Border**: `#1E293B`

### 3.2 Font Usage Principles

- **Title**: "Liter" Bold
- **Body**: "QuattrocentoSans"
- **KPI**: "Liter" Bold
- Font sizes: hero 48-52, title 28-32, subtitle 20-22, body 18-20, caption 13-14, badge 12

### 3.3 Container Styles

- Sharp corners (0-2px)
- Border 1px solid
- No shadows — flat dark design

### 3.4 Image Style

- Solid icons (fas)
- Tables minimal dark
- High-quality dark fitness/tech images for covers

## 4. Layout System

- 1280x720
- Margins: 60px L/R, 50px T, 40px B
- Badge top-left: "FIXINTEL PRO"
- Bottom accent bar + page number

## 5. Style Usage Rules

Same as strategic profile with adjusted content focus.

## 6. Risk Prohibitions

- No blue/cyan primary
- No rounded rectangles
- Body font >= 18px
- No pure white backgrounds
- Accent used sparingly (< 10%)

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
    white: "#FFFFFF"
    chart1: "#0D9488"
    chart2: "#F97316"
    chart3: "#64748B"
    chart4: "#10B981"
  textStyles:
    heroTitle:
      fontSize: 52
      color: "$white"
      fontFamily: "Liter"
      lineHeight: 1.1
      letterSpacing: 1
    title:
      fontSize: 32
      color: "$text"
      fontFamily: "Liter"
      lineHeight: 1.2
    subtitle:
      fontSize: 22
      color: "$secondary"
      fontFamily: "QuattrocentoSans"
      lineHeight: 1.3
    sectionTitle:
      fontSize: 24
      color: "$text"
      fontFamily: "Liter"
      lineHeight: 1.3
    body:
      fontSize: 18
      color: "$text"
      fontFamily: "QuattrocentoSans"
      lineHeight: 1.6
    bodySmall:
      fontSize: 16
      color: "$secondary"
      fontFamily: "QuattrocentoSans"
      lineHeight: 1.5
    kpi:
      fontSize: 56
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
      fontSize: 15
      fontFamily: "QuattrocentoSans"
      headerFill: "$primary"
      headerColor: "$white"
      headerBold: true
      bodyFill: ["$background", "$surface"]
      bodyColor: "$text"
      border:
        style: solid
        width: 1
        color: "$border"
    minimal:
      fontSize: 15
      fontFamily: "QuattrocentoSans"
      headerFill: "$surface"
      headerColor: "$primary"
      headerBold: true
      headerBorder: [null, null, {style: solid, width: 2, color: "$primary"}, null]
      bodyFill: ["$background"]
      bodyColor: "$text"
      bodyBorder: [null, null, {style: solid, width: 1, color: "$border"}, null]
      lastRowBorder: [null, null, {style: solid, width: 2, color: "$primary"}, null]
```
