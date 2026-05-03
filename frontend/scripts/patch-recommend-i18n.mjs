/**
 * One-off style patcher: merges `recommend` subtree (reason/color/fit/sceneNote) into en/zh/ko.json
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const localesDir = path.join(__dirname, "../src/i18n/locales");

const primaries = [
  "short_height",
  "leg_short",
  "belly",
  "broad_shoulders",
  "thick_thighs",
  "narrow_shoulders",
  "slim",
  "muscular",
  "athletic",
  "stocky",
  "balanced",
];
const budgets = ["low", "mid", "high"];
const scenes = ["daily", "date", "interview", "travel", "school", "work"];
const styleCats = ["minimal", "business", "casual"];

const enReasonBody = {
  short_height:
    "Shorter stature: prioritize cropped outerwear, a defined waist, and slightly lifted footwear to lengthen the leg line.",
  leg_short:
    "Shorter leg ratio: cropped outerwear, high-rise bottoms, and clean vertical lines help stretch the lower body visually.",
  belly:
    "Midsection needs ease: relaxed drape on top with a higher waist on bottoms keeps the silhouette calm and flattering.",
  broad_shoulders:
    "Broad shoulders: simplify upper-body detail and add balanced volume through trousers to keep proportions even.",
  thick_thighs:
    "Stronger thighs: straight or relaxed tapered pants read cleaner than skinny fits for everyday comfort.",
  narrow_shoulders:
    "Narrow shoulders: layering, structured collars, and light shoulder definition add presence without bulk.",
  slim:
    "Lean build: light layering and gentle volume add shape without overwhelming the frame.",
  muscular:
    "Muscular build: controlled silhouettes up top with straight legs keep the outfit relaxed, not overly tight.",
  athletic:
    "Athletic frame: easy room through the chest and shoulders with clean leg lines keeps the look natural.",
  stocky:
    "Stockier build: vertical lines, low-contrast color blocks, and steady proportions reduce horizontal emphasis.",
  balanced:
    "Balanced proportions: neat tailoring and a clear waistline keep everyday outfits sharp and easy to wear.",
};

const enBudgetHint = {
  low: "Tight budget: focus on a strong core trio and fewer competing pieces.",
  mid: "Mid budget: balance fabric quality with versatility across weekdays.",
  high: "Higher budget: you can add finishing layers and accessories for a more complete kit.",
};

const enColor = {
  daily_minimal: "Muted neutrals with one quiet accent — easy for commuting and errands.",
  daily_business: "Navy, charcoal, and crisp white for a calm weekday office tone.",
  daily_casual: "Soft neutrals with denim-friendly blues for relaxed daily wear.",
  date_minimal: "Restrained contrast: one soft highlight against a neutral base.",
  date_business: "Polished neutrals with subtle texture for a smart-casual evening.",
  date_casual: "Warm mid-tones that feel approachable without looking overstyled.",
  interview_minimal: "Clean, low-noise neutrals that read confident and composed.",
  interview_business: "Classic suit-adjacent neutrals with minimal pattern noise.",
  interview_casual: "Neat separates in conservative tones — relaxed but still respectful.",
  travel_minimal: "Packable neutrals that mix easily across multiple outfits.",
  travel_business: "Dark, wrinkle-friendly neutrals that still look pulled together.",
  travel_casual: "Comfort-first neutrals with one bright accent for photos and daytime walks.",
  school_minimal: "Simple palettes that stay tidy between classes and study blocks.",
  school_business: "Smart-casual neutrals suitable for presentations or club fairs.",
  school_casual: "Easy-going colors that pair with sneakers and backpacks.",
  work_minimal: "Desk-to-dinner neutrals with crisp contrast at collars and cuffs.",
  work_business: "Structured neutrals with controlled shine — boardroom friendly.",
  work_casual: "Relaxed tailoring colors: soft blues, greys, and off-white layers.",
};

const enFit = {
  vertical_emphasis: "Use vertical lines, higher rises, and shorter jackets to lift the eye upward.",
  upper_simple_lower_volume: "Keep the upper body clean and let trousers carry balanced volume.",
  waist_definition_drape: "Define the waist softly with drape rather than clingy layers.",
  balanced_silhouette: "Balance top and bottom weight with steady, straight leg lines.",
  athletic_trim: "Maintain easy room through the shoulders while keeping legs streamlined.",
};

const enSceneNote = {
  daily: "Framed for everyday routines: campus, errands, and casual social blocks.",
  date: "Tuned for closer social distance: cafés, galleries, and evening strolls.",
  interview: "Keeps formality cues clear while staying comfortable under pressure.",
  travel: "Built for movement: airports, city walking, and changing temperatures.",
  school: "Practical for long days on foot with simple layering options.",
  work: "Anchored to desk-to-meeting rhythms with neat, low-fuss upkeep.",
};

function buildReason(lang) {
  const out = {};
  for (const p of primaries) {
    for (const b of budgets) {
      const k = `${p}_${b}`;
      if (lang === "en") {
        out[k] = `${enReasonBody[p]} ${enBudgetHint[b]}`;
      } else if (lang === "zh") {
        out[k] = zhReason(k, p, b);
      } else {
        out[k] = koReason(k, p, b);
      }
    }
  }
  return out;
}

function zhReason(_k, p, b) {
  const body = {
    short_height: "身高偏矮：用短外套、明确腰线与略增高的鞋型拉长下半身比例。",
    leg_short: "腿身比偏短：短外套、高腰下装与纵向线条有助于视觉拉长腿部。",
    belly: "腰腹需要余量：上装垂坠、下装高腰，整体更从容修饰。",
    broad_shoulders: "肩较宽：简化上半身细节，用下装量感平衡整体比例。",
    thick_thighs: "大腿偏粗：直筒或略宽松锥形裤比紧身裤更日常好穿。",
    narrow_shoulders: "肩偏窄：叠穿、领口层次与轻结构外套增加上半身存在感。",
    slim: "偏瘦体型：轻叠穿与适度廓形增加体积感而不显臃肿。",
    muscular: "肌肉感明显：上身控制膨胀感，直筒裤保持松弛自然。",
    athletic: "运动骨架：胸肩留余量，腿部线条保持利落。",
    stocky: "偏厚实：纵向线条与低对比色块，减少横向扩张感。",
    balanced: "比例均衡：合身剪裁与清晰腰线即可保持利落日常感。",
  }[p];
  const budget = {
    low: "预算偏紧：优先核心三件，控制单品数量。",
    mid: "预算适中：在质感与通勤实穿性之间平衡。",
    high: "预算充足：可增加层次与配饰完成度。",
  }[b];
  return `${body}${budget}`;
}

function koReason(_k, p, b) {
  const body = {
    short_height: "키가 작게 느껴질 때: 짧은 아우터, 허리 라인, 살짝 올라오는 신발로 다리 비율을 보정해요.",
    leg_short: "다리 비율이 짧게 느껴질 때: 하이웨이스트와 세로 라인으로 시각적으로 길어 보이게 해요.",
    belly: "복부 라인이 신경 쓰일 때: 상의는 드레이프, 하의는 하이웨이스트로 여유 있게 정리해요.",
    broad_shoulders: "어깨가 넓을 때: 상체는 심플하게, 하의로 밸런스를 맞춰요.",
    thick_thighs: "허벅지가 굵은 편일 때: 스키니보다 스트레이트·살짝 테이퍼드가 편해요.",
    narrow_shoulders: "어깨가 좁을 때: 레이어링과 카라·가벼운 구조감으로 상체 존재감을 더해요.",
    slim: "마른 체형일 때: 가벼운 레이어링과 적당한 볼륨으로 실루엣을 살려요.",
    muscular: "근육이 뚜렷할 때: 상체는 과한 볼륨을 줄이고 하의는 스트레이트로 균형을 잡아요.",
    athletic: "운동형 골격일 때: 어깨·가슴 여유와 깔끔한 하의 라인이 자연스러워요.",
    stocky: "탄탄한 체형일 때: 세로 라인과 낮은 대비로 옆면 확장을 줄여요.",
    balanced: "균형 잡힌 비율일 때: 핏 좋은 재단과 허리 포인트로 데일리하게 유지해요.",
  }[p];
  const budget = {
    low: "예산이 타이트할 때: 핵심 3피스에 집중해요.",
    mid: "중간 예산: 실용성과 소재감의 밸런스를 맞춰요.",
    high: "여유 예산: 레이어와 액세서리로 완성도를 높일 수 있어요.",
  }[b];
  return `${body} ${budget}`;
}

function buildColor(lang) {
  const out = {};
  for (const s of scenes) {
    for (const c of styleCats) {
      const k = `${s}_${c}`;
      out[k] =
        lang === "en"
          ? enColor[k]
          : lang === "zh"
            ? zhColor(k)
            : koColor(k);
    }
  }
  return out;
}

function zhColor(k) {
  const map = {
    daily_minimal: "日常 + 极简：低饱和中性色，点缀一处安静亮色。",
    daily_business: "日常 + 商务：藏青、炭灰与干净白衬衫感的工作日基调。",
    daily_casual: "日常 + 休闲：柔和中性色配牛仔蓝，轻松出门。",
    date_minimal: "约会 + 极简：克制的对比，中性底上一抹柔和高光。",
    date_business: "约会 + 商务：有质感的深色中性，偏智性休闲晚装。",
    date_casual: "约会 + 休闲：偏暖的中性色，亲切不过度造型。",
    interview_minimal: "面试 + 极简：干净低噪中性色，稳重自信。",
    interview_business: "面试 + 商务：经典套装感中性色，花纹克制。",
    interview_casual: "面试 + 休闲：整洁分身搭配，偏保守色调。",
    travel_minimal: "旅行 + 极简：可混搭的中性色，行李箱友好。",
    travel_business: "旅行 + 商务：不易皱的深色中性，移动中也体面。",
    travel_casual: "旅行 + 休闲：舒适中性色，一点亮色适合白天拍照。",
    school_minimal: "校园 + 极简：简洁配色，课间也利落。",
    school_business: "校园 + 商务：适合发表/路演的智性休闲中性色。",
    school_casual: "校园 + 休闲：运动鞋与双肩包也好搭的轻松色。",
    work_minimal: "通勤 + 极简：领口袖口有清晰对比的桌面到晚宴中性色。",
    work_business: "通勤 + 商务：结构感中性色，光泽克制会议室友好。",
    work_casual: "通勤 + 休闲：柔和蓝灰与米白层的轻松正装感。",
  };
  return map[k] || k;
}

function koColor(k) {
  const map = {
    daily_minimal: "데일리+미니멀: 낮은 채도의 뉴트럴에 포인트 한 톤.",
    daily_business: "데일리+비즈니스: 네이비·차콜·화이트 셔츠 톤.",
    daily_casual: "데일리+캐주얼: 부드러운 뉴트럴과 데님 블루.",
    date_minimal: "데이트+미니멀: 뉴트럴 베이스에 은은한 포인트.",
    date_business: "데이트+비즈니스: 질감 있는 딥 뉴트럴 스마트 캐주얼.",
    date_casual: "데이트+캐주얼: 따뜻한 미드톤으로 부담 없이.",
    interview_minimal: "면접+미니멀: 깨끗한 저채도 뉴트럴.",
    interview_business: "면접+비즈니스: 클래식 수트 톤, 패턴 최소화.",
    interview_casual: "면접+캐주얼: 단정한 세퍼레이트, 보수적인 색감.",
    travel_minimal: "여행+미니멀: 믹스앤매치 쉬운 뉴트럴.",
    travel_business: "여행+비즈니스: 구김 덜한 다크 뉴트럴.",
    travel_casual: "여행+캐주얼: 편한 뉴트럴에 주간 포인트 한 컬러.",
    school_minimal: "학교+미니멀: 간결한 팔레트.",
    school_business: "학교+비즈니스: 발표에도 무리 없는 스마트 캐주얼 뉴트럴.",
    school_casual: "학교+캐주얼: 스니커·백팩과 어울리는 밝은 뉴트럴.",
    work_minimal: "출근+미니멀: 칼라·커프 대비가 살아 있는 뉴트럴.",
    work_business: "출근+비즈니스: 구조감 뉴트럴, 광택 절제.",
    work_casual: "출근+캐주얼: 소프트 블루·그레이·오프화이트 레이어.",
  };
  return map[k] || k;
}

function buildFit(lang) {
  const keys = Object.keys(enFit);
  const out = {};
  for (const k of keys) {
    out[k] =
      lang === "en"
        ? enFit[k]
        : lang === "zh"
          ? zhFit(k)
          : koFit(k);
  }
  return out;
}

function zhFit(k) {
  const map = {
    vertical_emphasis: "纵向线条、更高腰线与较短外套，把视觉向上引导。",
    upper_simple_lower_volume: "上半身简洁，用裤装量感平衡比例。",
    waist_definition_drape: "用垂坠与腰线定义腰腹，而非贴身堆叠。",
    balanced_silhouette: "上下量感平衡，直筒腿线稳住整体。",
    athletic_trim: "肩胸留余量，腿部线条保持利落。",
  };
  return map[k] || k;
}

function koFit(k) {
  const map = {
    vertical_emphasis: "세로 라인·하이웨이스트·짧은 아우터로 시선을 위로.",
    upper_simple_lower_volume: "상체는 심플, 하의로 볼륨 밸런스.",
    waist_definition_drape: "드레이프와 허리 포인트로 복부 정리.",
    balanced_silhouette: "상하 밸런스와 스트레이트 실루엣.",
    athletic_trim: "어깨·가슴 여유와 깔끔한 하의 라인.",
  };
  return map[k] || k;
}

function buildSceneNote(lang) {
  const out = {};
  for (const s of scenes) {
    out[s] =
      lang === "en"
        ? enSceneNote[s]
        : lang === "zh"
          ? zhSceneNote(s)
          : koSceneNote(s);
  }
  return out;
}

function zhSceneNote(s) {
  const map = {
    daily: "面向日常：通勤、办事与轻松社交。",
    date: "面向约会：咖啡馆、展馆与晚间散步。",
    interview: "面向面试：保持得体与可信赖感。",
    travel: "面向旅行：步行、温差与换乘场景。",
    school: "面向校园：长时间走动与简单叠穿。",
    work: "面向工作：工位到会议的节奏。",
  };
  return map[s] || s;
}

function koSceneNote(s) {
  const map = {
    daily: "데일리 루틴: 출근·심부름·가벼운 모임.",
    date: "데이트: 카페·전시·저녁 산책.",
    interview: "면접: 단정함과 신뢰감.",
    travel: "여행: 이동·걷기·기온 변화.",
    school: "캠퍼스: 장시간 이동과 레이어링.",
    work: "업무: 책상에서 회의까지.",
  };
  return map[s] || s;
}

for (const lang of ["en", "zh", "ko"]) {
  const p = path.join(localesDir, `${lang}.json`);
  const j = JSON.parse(fs.readFileSync(p, "utf8"));
  j.recommend = {
    reason: buildReason(lang),
    color: buildColor(lang),
    fit: buildFit(lang),
    sceneNote: buildSceneNote(lang),
  };
  // Rename recommendation label keys to avoid collision with copy text
  j.recommendation.reasonLabel = j.recommendation.reason;
  j.recommendation.colorLabel = j.recommendation.colorLogic;
  j.recommendation.fitLabel = j.recommendation.proportionTip;
  delete j.recommendation.reason;
  delete j.recommendation.colorLogic;
  delete j.recommendation.proportionTip;
  delete j.recommendation.outfitCopyTodo;
  fs.writeFileSync(p, JSON.stringify(j, null, 2) + "\n");
}
console.log("patched recommend.* into", localesDir);
