const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, BorderStyle, WidthType, ShadingType,
  LevelFormat, PageNumber, PageBreak, Header, Footer, TabStopType,
  TabStopPosition, VerticalAlign
} = require("docx");
const fs = require("fs");

// ─── Styles & Helpers ─────────────────────────────────────────────────────────

const COLORS = {
  navy: "0A3D62", teal: "0E7490", lightTeal: "CFFAFE", darkText: "1E293B",
  muted: "64748B", white: "FFFFFF", lightGray: "F1F5F9", midGray: "CBD5E1",
  red: "DC2626", amber: "D97706", green: "059669", border: "E2E8F0"
};

const border = { style: BorderStyle.SINGLE, size: 1, color: COLORS.border };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };

function heading1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, bold: true, font: "Arial", size: 36, color: COLORS.navy })],
    spacing: { before: 400, after: 200 },
  });
}

function heading2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, bold: true, font: "Arial", size: 28, color: COLORS.teal })],
    spacing: { before: 300, after: 150 },
  });
}

function heading3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children: [new TextRun({ text, bold: true, font: "Arial", size: 24, color: COLORS.darkText })],
    spacing: { before: 200, after: 100 },
  });
}

function body(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, font: "Arial", size: 22, color: COLORS.darkText, ...opts })],
    spacing: { before: 100, after: 100 },
    alignment: AlignmentType.JUSTIFIED,
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "bullets", level },
    children: [new TextRun({ text, font: "Arial", size: 22, color: COLORS.darkText })],
    spacing: { before: 60, after: 60 },
  });
}

function numbered(text, level = 0) {
  return new Paragraph({
    numbering: { reference: "numbers", level },
    children: [new TextRun({ text, font: "Arial", size: 22, color: COLORS.darkText })],
    spacing: { before: 60, after: 60 },
  });
}

function spacer(n = 1) {
  return Array(n).fill(new Paragraph({ children: [new TextRun("")], spacing: { before: 100, after: 100 } }));
}

function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

function colorRow(cells, bgColor) {
  return new TableRow({
    children: cells.map((text, i) => new TableCell({
      borders,
      width: { size: i === 0 ? 2800 : 1600, type: WidthType.DXA },
      shading: { fill: bgColor, type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      children: [new Paragraph({
        children: [new TextRun({ text: String(text), font: "Arial", size: 20, bold: i === 0, color: COLORS.darkText })],
        alignment: i > 0 ? AlignmentType.CENTER : AlignmentType.LEFT,
      })]
    }))
  });
}

// ─── NUMBERING CONFIG ─────────────────────────────────────────────────────────

const numbering = {
  config: [
    {
      reference: "bullets",
      levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 1080, hanging: 360 } } } },
      ]
    },
    {
      reference: "numbers",
      levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
      ]
    }
  ]
};

// ─── SHARED STYLES ────────────────────────────────────────────────────────────

const styles = {
  default: { document: { run: { font: "Arial", size: 22 } } },
  paragraphStyles: [
    { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 36, bold: true, font: "Arial", color: COLORS.navy },
      paragraph: { spacing: { before: 400, after: 200 }, outlineLevel: 0 } },
    { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 28, bold: true, font: "Arial", color: COLORS.teal },
      paragraph: { spacing: { before: 300, after: 150 }, outlineLevel: 1 } },
    { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 24, bold: true, font: "Arial", color: COLORS.darkText },
      paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
  ]
};

const pageProps = {
  size: { width: 12240, height: 15840 },
  margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
};

// ═══════════════════════════════════════════════════════════════════════════════
// DOCUMENT 1: CRAFTS SCORECARD
// ═══════════════════════════════════════════════════════════════════════════════

async function buildCRAFTSScorecard() {
  const headers = ["Dimension", "Criterion", "Score (1–5)", "Remarks"];
  const widths = [1500, 3500, 1500, 2860];

  function makeHeaderRow() {
    return new TableRow({
      tableHeader: true,
      children: headers.map((h, i) => new TableCell({
        borders, width: { size: widths[i], type: WidthType.DXA },
        shading: { fill: COLORS.navy, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: h, bold: true, font: "Arial", size: 20, color: COLORS.white })], alignment: AlignmentType.CENTER })]
      }))
    });
  }

  function makeRow(dim, criterion, score, remarks, shade) {
    const texts = [dim, criterion, score, remarks];
    return new TableRow({
      children: texts.map((t, i) => new TableCell({
        borders,
        width: { size: widths[i], type: WidthType.DXA },
        shading: { fill: shade, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: String(t), font: "Arial", size: 20, color: COLORS.darkText })], alignment: i === 2 ? AlignmentType.CENTER : AlignmentType.LEFT })]
      }))
    });
  }

  const rows = [
    makeHeaderRow(),
    makeRow("C — Clarity", "Problem is clearly defined and bounded", "5", "One coastal habitat; one scarcity problem; one pipeline", COLORS.lightGray),
    makeRow("", "Primary and specific objectives are stated", "5", "5 specific objectives covering sensing, detection, LLM, evaluation", COLORS.white),
    makeRow("", "Success condition is measurable", "4", "Detection accuracy and briefing usefulness are evaluable", COLORS.lightGray),
    makeRow("R — Research", "Grounded in relevant literature", "4", "Ecosystem stress, biodiversity, IoT monitoring, LLM summarization", COLORS.white),
    makeRow("", "Research gap clearly identified", "5", "Combines scarcity detection + LLM briefing — not done before", COLORS.lightGray),
    makeRow("", "Conceptual/theoretical basis present", "4", "Ecosystem stress theory + anomaly detection + biodiversity indicators", COLORS.white),
    makeRow("A — Alignment", "Fits capstone requirements", "5", "Prototype-focused; defensible scope; novel system", COLORS.lightGray),
    makeRow("", "Ethical considerations addressed", "5", "Non-invasive sensors; no harmful sampling", COLORS.white),
    makeRow("", "Scope is manageable", "4", "One coastal site, one sensor suite, one LLM pipeline", COLORS.lightGray),
    makeRow("F — Feasibility", "Technical feasibility confirmed", "4", "Simulated mode + Raspberry Pi path; both tested", COLORS.white),
    makeRow("", "Economic feasibility is acceptable", "5", "Low-cost sensors; open-source stack; affordable cloud LLM", COLORS.lightGray),
    makeRow("", "Schedule is realistic", "4", "Prototype + evaluation + defense within semester timeline", COLORS.white),
    makeRow("T — Thesis", "Methodology follows a traceable pipeline", "5", "Sense → Detect → Analyze → Brief → Store → Alert", COLORS.lightGray),
    makeRow("", "Evaluation criteria are defined", "4", "Detection accuracy, false alert rate, briefing usefulness, uptime", COLORS.white),
    makeRow("", "Output quality is defined", "5", "Event logs, briefings, dashboard, scarcity trend", COLORS.lightGray),
    makeRow("S — Submission", "Manuscript chapters consistent", "4", "All objectives trace to methods; results trace to conclusions", COLORS.white),
    makeRow("", "Defense materials planned", "4", "Slides, demo script, architecture diagram, evaluation summary", COLORS.lightGray),
    makeRow("", "Final outputs ready for submission", "4", "Code, docs, test results, prototype deployment notes", COLORS.white),
  ];

  const summaryRow = new TableRow({
    children: [
      new TableCell({
        borders,
        columnSpan: 2,
        width: { size: 5000, type: WidthType.DXA },
        shading: { fill: COLORS.navy, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: "TOTAL SCORE", bold: true, font: "Arial", size: 22, color: COLORS.white })] })]
      }),
      new TableCell({
        borders,
        width: { size: 1500, type: WidthType.DXA },
        shading: { fill: COLORS.teal, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: "76 / 85", bold: true, font: "Arial", size: 22, color: COLORS.white })], alignment: AlignmentType.CENTER })]
      }),
      new TableCell({
        borders,
        width: { size: 2860, type: WidthType.DXA },
        shading: { fill: COLORS.navy, type: ShadingType.CLEAR },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [new Paragraph({ children: [new TextRun({ text: "RECOMMENDED FOR DEVELOPMENT", bold: true, font: "Arial", size: 20, color: COLORS.lightTeal })] })]
      }),
    ]
  });

  rows.push(summaryRow);

  return new Document({
    numbering, styles,
    sections: [{
      properties: { page: pageProps },
      children: [
        new Paragraph({
          children: [new TextRun({ text: "CatchFade", font: "Arial", size: 56, bold: true, color: COLORS.navy })],
          alignment: AlignmentType.CENTER, spacing: { before: 400, after: 100 }
        }),
        new Paragraph({
          children: [new TextRun({ text: "CRAFTS Framework Scorecard", font: "Arial", size: 32, color: COLORS.teal })],
          alignment: AlignmentType.CENTER, spacing: { before: 0, after: 80 }
        }),
        new Paragraph({
          children: [new TextRun({ text: "A Self-Operating Aquatic Scarcity Detection System for Coastal/Marine Monitoring", font: "Arial", size: 22, color: COLORS.muted, italics: true })],
          alignment: AlignmentType.CENTER, spacing: { before: 0, after: 400 }
        }),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1500, 3500, 1500, 2860],
          rows,
        }),
        ...spacer(2),
        heading2("CRAFTS Verdict"),
        body("CatchFade earns a score of 76 out of 85 points across the CRAFTS framework, qualifying it as ready for full capstone development. The system demonstrates exceptional clarity of scope, a well-identified research gap, and a technically feasible prototype pathway using off-the-shelf components."),
        body("The primary risk area is schedule feasibility, which requires the team to maintain strict scope discipline — one coastal habitat type, one sensor fusion pipeline, and one LLM briefing workflow. Expansion to multiple sites or sensor types should be deferred to future work."),
        ...spacer(1),
        heading2("Key Strengths"),
        bullet("Original concept combining aquatic scarcity detection with LLM ecological interpretation"),
        bullet("Autonomous by design — minimal human intervention after deployment"),
        bullet("Strong academic relevance to marine ecology, IoT sensing, and AI-assisted environmental monitoring"),
        bullet("Simulated mode enables full development without hardware"),
        bullet("Multi-provider LLM support (Anthropic Claude, OpenAI GPT, Ollama local)"),
        ...spacer(1),
        heading2("Improvement Areas"),
        bullet("Formalize literature review with minimum 20 peer-reviewed sources"),
        bullet("Define evaluation metrics quantitatively before data collection begins"),
        bullet("Confirm field deployment site or formalize simulation parameters as a valid proxy"),
      ]
    }]
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// DOCUMENT 2: CHAPTER 1 — INTRODUCTION
// ═══════════════════════════════════════════════════════════════════════════════

async function buildChapter1() {
  return new Document({
    numbering, styles,
    sections: [{
      properties: { page: pageProps },
      children: [
        new Paragraph({
          children: [new TextRun({ text: "CatchFade", font: "Arial", size: 56, bold: true, color: COLORS.navy })],
          alignment: AlignmentType.CENTER, spacing: { before: 400, after: 100 }
        }),
        new Paragraph({
          children: [new TextRun({ text: "A Self-Operating Aquatic Scarcity Detection System for Monitoring Species Decline and Ecological Stress in Coastal/Marine Environments", font: "Arial", size: 24, color: COLORS.teal, italics: true })],
          alignment: AlignmentType.CENTER, spacing: { before: 0, after: 400 }
        }),
        heading1("Chapter 1: Introduction"),
        heading2("1.1 Background of the Study"),
        body("Coastal and marine ecosystems are among the most biologically diverse and ecologically productive environments on Earth. Coral reefs, seagrass beds, mangrove forests, and open coastal waters support an estimated 25 percent of all marine species and provide critical ecosystem services including food security, coastal protection, carbon sequestration, and livelihood support for billions of people worldwide (Costanza et al., 2014). However, these environments are under unprecedented anthropogenic pressure from climate change, ocean acidification, overfishing, and habitat destruction."),
        body("The detection of species decline and ecological stress in marine environments presents a formidable challenge. Traditional monitoring approaches rely heavily on manual field surveys, which are limited by geographic access constraints, sampling frequency, observer subjectivity, and high operational costs. By the time declining species abundances or critical habitat degradation events are identified through manual observation, ecological thresholds may have already been crossed — rendering intervention significantly more difficult and costly."),
        body("Recent advances in low-cost sensor technology, edge computing, and artificial intelligence offer a transformative opportunity for continuous, autonomous, and intelligent aquatic monitoring. Multi-parameter sensor systems capable of measuring water temperature, salinity, dissolved oxygen, turbidity, and pH can collectively characterize the physical and chemical state of a marine habitat with sufficient resolution to detect anomalous conditions associated with species stress and decline. When combined with hydroacoustic monitoring — which detects the characteristic bioacoustic signatures of reef fish choruses, snapping shrimp, and marine mammals — autonomous systems can infer biological activity levels and detect acoustic silence as a proxy for species displacement or absence."),
        body("Large language models (LLMs) represent a novel capability for ecological interpretation. Rather than presenting raw sensor data to human operators — who may lack the domain expertise to interpret complex multi-parameter patterns — LLM-based systems can generate natural-language ecological briefings that synthesize sensor readings into actionable ecological intelligence. This capability has significant implications for democratizing access to marine ecological monitoring, particularly in resource-limited contexts where expert marine biologists are unavailable for continuous site monitoring."),
        ...spacer(1),
        heading2("1.2 Statement of the Problem"),
        body("Coastal and marine ecosystems in the Philippines and across Southeast Asia are experiencing accelerating degradation, with coral reef cover declining by an estimated 50 percent over the past three decades (Burke et al., 2011). Despite the ecological and economic significance of these ecosystems, real-time autonomous monitoring systems that combine physical-chemical sensing, biological activity detection, and intelligent ecological interpretation remain largely absent from deployment in coastal management practice."),
        body("Existing monitoring approaches suffer from three fundamental limitations. First, manual survey-based monitoring provides only episodic temporal coverage, creating significant data gaps between observations. Second, standalone water quality monitoring systems provide physicochemical data without ecological context, limiting their utility for species conservation decision-making. Third, the absence of automated interpretation tools means that even when monitoring data is collected, its translation into actionable ecological intelligence requires expert human intervention that is not always available."),
        body("CatchFade addresses this gap by designing, implementing, and evaluating a self-operating aquatic monitoring system that autonomously detects species scarcity indicators and ecological stress conditions in coastal marine environments, and generates human-readable ecological briefings using large language models."),
        ...spacer(1),
        heading2("1.3 Objectives of the Study"),
        heading3("General Objective"),
        body("To design, implement, and evaluate CatchFade — a self-operating aquatic scarcity detection system that autonomously monitors species decline and ecological stress in coastal marine environments through multi-parameter sensing, anomaly detection, and LLM-generated ecological briefing."),
        heading3("Specific Objectives"),
        numbered("To identify and characterize the environmental parameters most strongly associated with species scarcity and ecological stress in coastal marine habitats, with particular attention to dissolved oxygen, temperature, salinity, pH, turbidity, and bioacoustic activity."),
        numbered("To design and implement an autonomous sensor data collection pipeline capable of operating continuously with minimal human intervention, including offline buffering and edge-based preprocessing."),
        numbered("To develop and validate an anomaly detection engine that identifies deviations from established marine environmental baselines and classifies detected anomalies by type, severity, and ecological significance."),
        numbered("To integrate a large language model API into the system pipeline to generate structured ecological briefings from detected anomaly patterns, and to evaluate the ecological accuracy and practical utility of generated briefings."),
        numbered("To evaluate the overall performance of the CatchFade system against defined metrics of detection accuracy, false alert rate, briefing relevance, system uptime, and data completeness."),
        ...spacer(1),
        heading2("1.4 Significance of the Study"),
        body("This study makes four principal contributions to the fields of environmental informatics, marine ecology, and intelligent monitoring systems."),
        body("First, CatchFade advances the state of practice in autonomous aquatic monitoring by integrating biological activity sensing (hydroacoustics, motion detection) with physicochemical sensing in a single, self-operating system. This integration enables scarcity detection that goes beyond water quality assessment to infer species presence and behavioral patterns."),
        body("Second, the incorporation of large language model-generated ecological briefings represents a novel application of generative AI to environmental monitoring. By producing natural-language interpretations of sensor-detected anomalies, CatchFade lowers the barrier to actionable ecological intelligence for non-expert stakeholders including coastal managers, local government units, and community-based resource managers."),
        body("Third, the system's modular architecture — supporting both simulated and hardware deployment modes, and multiple LLM provider backends — provides a replicable and extensible framework for future deployment across diverse coastal monitoring contexts in the Philippines and the broader Indo-Pacific region."),
        body("Fourth, this study generates empirical evaluation data on the feasibility of autonomous AI-assisted marine monitoring, contributing evidence to the growing literature on intelligent environmental monitoring systems in resource-limited settings."),
        ...spacer(1),
        heading2("1.5 Scope and Limitations"),
        body("CatchFade is scoped to coastal and marine habitat monitoring with a focus on the detection of species scarcity indicators through environmental parameter anomalies and bioacoustic signals. The system is designed for deployment in a single monitoring node configuration, with architecture supporting future multi-node expansion."),
        body("The following limitations apply to the current study:"),
        bullet("Species identification: CatchFade detects species absence or reduced activity through acoustic and physicochemical proxies. Direct species identification or abundance counting is outside the scope of this prototype."),
        bullet("Habitat coverage: The system is validated for coastal and open marine environments. Mangrove-specific, deep-water, or estuarine deployments may require additional sensor calibration."),
        bullet("LLM interpretation accuracy: Ecological briefings generated by LLMs are based on pattern recognition from training data and should be validated by qualified marine biologists before use in formal management decisions."),
        bullet("Long-term deployment: This study encompasses prototype development and initial evaluation. Long-term reliability under sustained field conditions — including biofouling, saltwater corrosion, and power management — is deferred to future work."),
        ...spacer(1),
        heading2("1.6 Definition of Terms"),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [2800, 6560],
          rows: [
            new TableRow({ tableHeader: true, children: [
              new TableCell({ borders, width: { size: 2800, type: WidthType.DXA }, shading: { fill: COLORS.navy, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "Term", bold: true, font: "Arial", size: 20, color: COLORS.white })] })] }),
              new TableCell({ borders, width: { size: 6560, type: WidthType.DXA }, shading: { fill: COLORS.navy, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "Definition", bold: true, font: "Arial", size: 20, color: COLORS.white })] })] }),
            ]}),
            ...([
              ["CatchFade", "A self-operating aquatic monitoring system designed to detect species decline and ecological stress through autonomous sensing and LLM-based ecological briefing generation."],
              ["Species Scarcity", "A condition in which the abundance or activity of one or more marine species at a monitored site falls significantly below established baseline levels, as inferred from environmental and bioacoustic indicators."],
              ["Ecological Stress", "A state of environmental departure from conditions that support normal biological activity, characterized by anomalous values in one or more physicochemical or biological monitoring parameters."],
              ["Dissolved Oxygen (DO)", "The concentration of oxygen dissolved in water, measured in mg/L, which is a primary determinant of the aerobic capacity of aquatic habitats and a sensitive indicator of hypoxic stress."],
              ["Acoustic Activity Index", "A normalized metric (0–1) derived from hydrophone data representing the intensity of biological sound production at the monitoring site, used as a proxy for species presence and activity."],
              ["Scarcity Score", "A composite metric (0.0–1.00) computed by CatchFade from detected anomalies, weighted by severity and co-occurrence, representing the likelihood of species scarcity at the monitoring site."],
              ["Ecological Briefing", "A structured natural-language report generated by a large language model (LLM) interpreting sensor data and detected anomalies in ecological context, including status, analysis, species risk, and recommended actions."],
              ["Anomaly Detection", "The computational process of identifying sensor readings that deviate significantly from established baselines or expected patterns, triggering further analysis or alert generation."],
              ["Edge Computing", "The practice of performing data processing on or near the monitoring device rather than in a centralized cloud server, enabling autonomous operation and offline capability."],
              ["LLM (Large Language Model)", "An artificial intelligence system trained on large text corpora, capable of generating coherent, contextually relevant natural-language text from structured or unstructured prompts."],
            ].map(([term, def], i) => new TableRow({
              children: [
                new TableCell({ borders, width: { size: 2800, type: WidthType.DXA }, shading: { fill: i % 2 === 0 ? COLORS.lightGray : COLORS.white, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: term, bold: true, font: "Arial", size: 20, color: COLORS.teal })] })] }),
                new TableCell({ borders, width: { size: 6560, type: WidthType.DXA }, shading: { fill: i % 2 === 0 ? COLORS.lightGray : COLORS.white, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: def, font: "Arial", size: 20, color: COLORS.darkText })] })] }),
              ]
            })))
          ]
        }),
      ]
    }]
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// DOCUMENT 3: CONCEPTUAL FRAMEWORK
// ═══════════════════════════════════════════════════════════════════════════════

async function buildConceptualFramework() {
  return new Document({
    numbering, styles,
    sections: [{
      properties: { page: pageProps },
      children: [
        new Paragraph({
          children: [new TextRun({ text: "CatchFade", font: "Arial", size: 56, bold: true, color: COLORS.navy })],
          alignment: AlignmentType.CENTER, spacing: { before: 400, after: 100 }
        }),
        new Paragraph({
          children: [new TextRun({ text: "Conceptual Framework", font: "Arial", size: 32, color: COLORS.teal })],
          alignment: AlignmentType.CENTER, spacing: { before: 0, after: 400 }
        }),
        heading1("Conceptual Framework"),
        body("The CatchFade conceptual framework integrates three foundational theoretical domains: ecosystem stress theory, autonomous environmental monitoring pipeline design, and LLM-assisted ecological interpretation. Together, these domains form a coherent conceptual architecture for a self-operating aquatic scarcity detection system."),
        ...spacer(1),
        heading2("Theoretical Anchors"),
        heading3("1. Ecosystem Stress Theory"),
        body("CatchFade is grounded in the ecosystem stress theory framework, which posits that ecological communities respond to environmental stressors through measurable changes in species composition, abundance, and behavior before collapse thresholds are reached (Rapport et al., 1985). The system operationalizes this theory by monitoring the physicochemical parameters most strongly correlated with marine ecosystem stress — dissolved oxygen, temperature, salinity, pH, and turbidity — and interpreting deviations from established baselines as early indicators of species scarcity."),
        heading3("2. Biodiversity Indicator Framework"),
        body("The system adopts a proxy-based approach to biodiversity monitoring, consistent with the Convention on Biological Diversity's framework for Essential Biodiversity Variables (EBVs). Rather than directly counting species, CatchFade monitors environmental conditions and bioacoustic signals that co-vary with species presence and abundance. Acoustic activity serves as a particularly powerful biodiversity indicator, reflecting the aggregate biotic activity of reef fish assemblages, invertebrate communities, and marine mammals through their characteristic sound production."),
        heading3("3. Autonomous Environmental Monitoring Pipeline"),
        body("The system architecture follows the IoT environmental monitoring pipeline model: sense, process, detect, respond. This pipeline is augmented in CatchFade by an LLM-based interpretation layer that transforms machine-detected anomalies into ecologically contextualized briefings, addressing the critical 'last mile' problem of translating data into actionable intelligence."),
        heading3("4. Multi-Stressor Interaction Model"),
        body("Marine ecosystems rarely experience single-parameter stress in isolation. CatchFade incorporates a multi-stressor weighting model in which the co-occurrence of multiple anomalous parameters amplifies the overall scarcity score and escalates alert severity. This approach reflects the documented synergistic effects of combined thermal, hypoxic, and acidification stressors on coral reef communities."),
        ...spacer(1),
        heading2("Conceptual Framework Diagram Description"),
        body("The CatchFade conceptual framework is organized as a five-layer hierarchical pipeline:"),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [1200, 2500, 5660],
          rows: [
            new TableRow({ tableHeader: true, children: [
              new TableCell({ borders, width: { size: 1200, type: WidthType.DXA }, shading: { fill: COLORS.navy, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "Layer", bold: true, font: "Arial", size: 20, color: COLORS.white })], alignment: AlignmentType.CENTER })] }),
              new TableCell({ borders, width: { size: 2500, type: WidthType.DXA }, shading: { fill: COLORS.navy, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "Component", bold: true, font: "Arial", size: 20, color: COLORS.white })] })] }),
              new TableCell({ borders, width: { size: 5660, type: WidthType.DXA }, shading: { fill: COLORS.navy, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: "Function", bold: true, font: "Arial", size: 20, color: COLORS.white })] })] }),
            ]}),
            ...([
              ["1 — INPUT", "Sensor Array", "Multi-parameter physicochemical sensors + hydrophone collect raw environmental data at configurable intervals. Data includes temperature, salinity, DO, pH, turbidity, depth, acoustic activity, motion, and light."],
              ["2 — PROCESS", "Edge Processing", "Raw sensor data is preprocessed on the edge device (Raspberry Pi or equivalent): noise filtering, unit conversion, timestamp normalization, and offline buffering for resilience against connectivity loss."],
              ["3 — DETECT", "Anomaly Detection Engine", "Processed readings are evaluated against established marine baselines using rule-based threshold comparison and statistical deviation analysis. Anomalies are classified by type and severity (Normal → Warning → Critical → Emergency). A composite Scarcity Score (0–1) and Stress Index (0–10) are computed."],
              ["4 — INTERPRET", "LLM Briefing Generator", "Detected anomalies and sensor context are submitted to a large language model (Claude, GPT, or Ollama) via structured prompt. The LLM generates a structured ecological briefing covering status, analysis, species risk, and recommended actions."],
              ["5 — OUTPUT", "Dashboard, Alerts, Storage", "Results are persisted to a local SQLite database, displayed on a real-time web dashboard, and (on threshold breach) dispatched as alerts. Briefings are archived with full traceability to source data."],
            ].map(([layer, comp, func], i) => new TableRow({
              children: [
                new TableCell({ borders, width: { size: 1200, type: WidthType.DXA }, shading: { fill: i % 2 === 0 ? COLORS.lightTeal : COLORS.white, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: layer, bold: true, font: "Arial", size: 19, color: COLORS.navy })], alignment: AlignmentType.CENTER })] }),
                new TableCell({ borders, width: { size: 2500, type: WidthType.DXA }, shading: { fill: i % 2 === 0 ? COLORS.lightTeal : COLORS.white, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: comp, bold: true, font: "Arial", size: 20, color: COLORS.teal })] })] }),
                new TableCell({ borders, width: { size: 5660, type: WidthType.DXA }, shading: { fill: i % 2 === 0 ? COLORS.lightGray : COLORS.white, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: func, font: "Arial", size: 20, color: COLORS.darkText })] })] }),
              ]
            })))
          ]
        }),
        ...spacer(1),
        heading2("Input → Process → Output (IPO) Model"),
        heading3("INPUTS"),
        bullet("Water temperature (°C) — thermal stress indicator"),
        bullet("Salinity (ppt) — osmotic stress indicator"),
        bullet("Dissolved oxygen (mg/L) — hypoxia indicator"),
        bullet("pH — ocean acidification indicator"),
        bullet("Turbidity (NTU) — light penetration indicator"),
        bullet("Acoustic activity index — species presence/absence proxy"),
        bullet("Motion detection — biological activity confirmation"),
        bullet("Ambient light — temporal context"),
        heading3("PROCESS"),
        bullet("Baseline comparison against established marine thresholds"),
        bullet("Rule-based anomaly classification (type, severity)"),
        bullet("Multi-stressor scarcity score computation"),
        bullet("LLM prompt engineering and ecological interpretation"),
        heading3("OUTPUTS"),
        bullet("Scarcity Score (0.0–1.00) — species decline likelihood"),
        bullet("Stress Index (0–10) — composite habitat health metric"),
        bullet("Ecological briefing — LLM-generated natural-language report"),
        bullet("Alert notifications — severity-triggered notifications"),
        bullet("Trend dashboard — real-time and historical visualization"),
        bullet("Archived event log — traceable detection history"),
        ...spacer(1),
        heading2("Operational Variables"),
        heading3("Independent Variables"),
        body("The independent variables in CatchFade are the physicochemical and biological environmental parameters measured by the sensor array: water temperature, salinity, dissolved oxygen, pH, turbidity, water depth, acoustic activity, and motion detection. These parameters collectively represent the environmental state of the monitored coastal habitat."),
        heading3("Dependent Variables"),
        body("The primary dependent variables are the Scarcity Score and the Stress Index, both of which are derived computationally from the pattern of detected anomalies across the independent variables. Secondary dependent variables include the severity classification of detected events and the ecological briefing quality score."),
        heading3("Moderating Variables"),
        body("Moderating variables include tidal cycle, time of day, seasonal variation, weather events, and anthropogenic activities (vessel traffic, fishing activity) that may influence environmental parameter readings independently of species scarcity conditions. The system controls for some of these through the temporal context provided by ambient light readings and timestamp data."),
      ]
    }]
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// DOCUMENT 4: PROBLEM STATEMENT & OBJECTIVES
// ═══════════════════════════════════════════════════════════════════════════════

async function buildProblemStatement() {
  return new Document({
    numbering, styles,
    sections: [{
      properties: { page: pageProps },
      children: [
        new Paragraph({
          children: [new TextRun({ text: "CatchFade", font: "Arial", size: 56, bold: true, color: COLORS.navy })],
          alignment: AlignmentType.CENTER, spacing: { before: 400, after: 100 }
        }),
        new Paragraph({
          children: [new TextRun({ text: "Problem Statement & Research Objectives", font: "Arial", size: 30, color: COLORS.teal })],
          alignment: AlignmentType.CENTER, spacing: { before: 0, after: 400 }
        }),
        heading1("Problem Statement"),
        body("Coastal marine ecosystems are among the most ecologically critical and economically valuable environments on Earth, yet they are experiencing accelerating decline due to the combined pressures of climate change, ocean acidification, and anthropogenic disturbance. In the Philippines — one of the world's most biodiverse marine nations — coral reef degradation, fish population collapse, and seagrass loss have reached crisis levels, with reef coverage declining from an estimated 27 percent in good condition to fewer than 1 percent in excellent condition over recent decades (Licuanan et al., 2019)."),
        body("The fundamental barrier to effective marine conservation is not the absence of policy frameworks or conservation intent, but the absence of timely, continuous, and intelligible ecological intelligence at the site level. Marine protected area managers, local government units, and coastal communities lack access to real-time data on the ecological condition of the habitats they are mandated to protect. When ecological stress events occur — hypoxic episodes, thermal bleaching events, salinity intrusions — they are often detected only after visible biological impacts have already materialized."),
        body("Current monitoring technologies address only partial dimensions of this problem. Standalone water quality monitoring stations provide physicochemical data but generate no ecological interpretation. Satellite-based sea surface temperature monitoring provides regional thermal context but lacks the temporal resolution and local specificity needed for site-level management. Manual biological surveys provide the most ecologically meaningful data but are prohibitively resource-intensive for continuous monitoring."),
        body("No existing operational system integrates: (1) continuous multi-parameter aquatic sensing, (2) bioacoustic species activity monitoring, (3) automated anomaly detection with ecological classification, and (4) natural-language ecological briefing generation through large language models — within a single self-operating platform designed for coastal/marine deployment."),
        body("CatchFade is designed to address this gap by developing and evaluating a prototype system that autonomously detects species scarcity and ecological stress in coastal marine environments and generates actionable ecological intelligence through LLM-based briefing — functioning as a persistent, intelligent ecological sentinel for coastal habitats."),
        ...spacer(1),
        heading1("Research Questions"),
        numbered("What environmental parameters, sensor configurations, and threshold conditions are most effective for detecting species scarcity and ecological stress in coastal/marine habitats?"),
        numbered("To what extent can an autonomous multi-parameter sensing pipeline reliably collect, preprocess, and store continuous environmental data in a coastal deployment scenario?"),
        numbered("How accurately does the CatchFade anomaly detection engine identify ecologically significant stress events compared to established marine baseline conditions, and what is the system's false alert rate?"),
        numbered("What is the ecological accuracy and practical utility of LLM-generated ecological briefings as assessed by domain experts in marine biology?"),
        numbered("What is the overall system performance of CatchFade across metrics of uptime, data completeness, detection accuracy, and briefing quality?"),
        ...spacer(1),
        heading1("Research Objectives"),
        heading2("General Objective"),
        new Paragraph({
          children: [new TextRun({ text: "To design, implement, and evaluate CatchFade — a self-operating aquatic scarcity detection system that autonomously monitors species decline and ecological stress in coastal marine environments through multi-parameter sensing, anomaly detection, and LLM-generated ecological briefing.", font: "Arial", size: 22, color: COLORS.darkText, bold: true })],
          spacing: { before: 100, after: 200 },
          alignment: AlignmentType.JUSTIFIED,
          border: { left: { style: BorderStyle.SINGLE, size: 12, color: COLORS.teal, space: 10 } },
          indent: { left: 400 },
        }),
        heading2("Specific Objectives"),
        new Table({
          width: { size: 9360, type: WidthType.DXA },
          columnWidths: [600, 3000, 3380, 2380],
          rows: [
            new TableRow({ tableHeader: true, children: [
              ...["#", "Objective", "Expected Output", "Evaluation Metric"].map((h, i) => new TableCell({
                borders, width: { size: [600,3000,3380,2380][i], type: WidthType.DXA },
                shading: { fill: COLORS.teal, type: ShadingType.CLEAR },
                margins: { top: 80, bottom: 80, left: 120, right: 120 },
                children: [new Paragraph({ children: [new TextRun({ text: h, bold: true, font: "Arial", size: 20, color: COLORS.white })], alignment: AlignmentType.CENTER })]
              }))
            ]}),
            ...([
              ["SO1", "Identify and characterize environmental parameters associated with species scarcity and ecological stress in coastal marine habitats.", "Parameter taxonomy with threshold definitions and ecological justification.", "Literature validation; expert review agreement rate ≥ 80%."],
              ["SO2", "Design and implement an autonomous sensor data collection pipeline with offline buffering and edge preprocessing.", "Functional sensor pipeline; buffered data storage; preprocessing module.", "Data completeness rate ≥ 95% over 72-hour test period."],
              ["SO3", "Develop and validate an anomaly detection engine classifying deviations by type, severity, and ecological significance.", "Anomaly detector with severity classification and scarcity scoring.", "Detection accuracy ≥ 85%; false positive rate ≤ 15%."],
              ["SO4", "Integrate LLM API for ecological briefing generation and evaluate briefing accuracy and utility.", "LLM briefing module; sample briefings; expert evaluation results.", "Expert-rated ecological accuracy ≥ 3.5/5.0; utility ≥ 3.5/5.0."],
              ["SO5", "Evaluate overall CatchFade system performance across defined metrics.", "System evaluation report with quantitative results.", "System uptime ≥ 90%; all SO metrics met."],
            ].map(([num, obj, output, metric], i) => new TableRow({
              children: [
                new TableCell({ borders, width: { size: 600, type: WidthType.DXA }, shading: { fill: i % 2 === 0 ? COLORS.lightGray : COLORS.white, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, verticalAlign: VerticalAlign.CENTER, children: [new Paragraph({ children: [new TextRun({ text: num, bold: true, font: "Arial", size: 20, color: COLORS.teal })], alignment: AlignmentType.CENTER })] }),
                new TableCell({ borders, width: { size: 3000, type: WidthType.DXA }, shading: { fill: i % 2 === 0 ? COLORS.lightGray : COLORS.white, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: obj, font: "Arial", size: 20, color: COLORS.darkText })] })] }),
                new TableCell({ borders, width: { size: 3380, type: WidthType.DXA }, shading: { fill: i % 2 === 0 ? COLORS.lightGray : COLORS.white, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: output, font: "Arial", size: 20, color: COLORS.darkText })] })] }),
                new TableCell({ borders, width: { size: 2380, type: WidthType.DXA }, shading: { fill: i % 2 === 0 ? COLORS.lightGray : COLORS.white, type: ShadingType.CLEAR }, margins: { top: 80, bottom: 80, left: 120, right: 120 }, children: [new Paragraph({ children: [new TextRun({ text: metric, font: "Arial", size: 20, color: COLORS.darkText })] })] }),
              ]
            })))
          ]
        }),
      ]
    }]
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// GENERATE ALL DOCUMENTS
// ═══════════════════════════════════════════════════════════════════════════════

async function main() {
  const outputDir = "/mnt/user-data/outputs";
  
  const docs = [
    { name: "CatchFade_CRAFTS_Scorecard.docx", fn: buildCRAFTSScorecard },
    { name: "CatchFade_Chapter1_Introduction.docx", fn: buildChapter1 },
    { name: "CatchFade_Conceptual_Framework.docx", fn: buildConceptualFramework },
    { name: "CatchFade_Problem_Statement_Objectives.docx", fn: buildProblemStatement },
  ];

  for (const { name, fn } of docs) {
    console.log(`Building ${name}...`);
    const doc = await fn();
    const buffer = await Packer.toBuffer(doc);
    const path = `${outputDir}/${name}`;
    fs.writeFileSync(path, buffer);
    console.log(`  ✓ Saved: ${path}`);
  }
  console.log("\nAll documents generated successfully!");
}

main().catch(console.error);
