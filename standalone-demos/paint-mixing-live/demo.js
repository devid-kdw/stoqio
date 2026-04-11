      const DEMO_CONFIG = {
        stoqio_base_url: "/api/v1",
        demo_username: "demo_operator",
        demo_password: "!Mitnica9942",
        scale: {
          stability_window_seconds: 3,
          stability_threshold_grams: 0.5,
          base_range_grams: { min: 200, max: 1500 },
        },
        hardener_tolerance_pct: 0.10,
        submit_countdown_seconds: 4,
      };

      const DEFAULT_VARIANT = "TOPCOAT";

      const MIXING_SYSTEMS = {
        "346-55:TOPCOAT": {
          system: "346-55",
          variant: "TOPCOAT",
          hardener_id: "345-55",
          hardener_article_no: "800072",
          base_to_hardener_ratio: 5,
          water_pct: 0.20,
          mixing_order: ["base", "hardener", "water"],
        },
        "346-55:TEXTURE": {
          system: "346-55",
          variant: "TEXTURE",
          hardener_id: "345-55",
          hardener_article_no: "800072",
          base_to_hardener_ratio: 5,
          water_pct: 0.10,
          mixing_order: ["base", "hardener", "water"],
        },
        "346-56:TOPCOAT": {
          system: "346-56",
          variant: "TOPCOAT",
          hardener_id: "345-55",
          hardener_article_no: "800072",
          base_to_hardener_ratio: 5,
          water_pct: 0.20,
          mixing_order: ["base", "hardener", "water"],
        },
        "346-56:TEXTURE": {
          system: "346-56",
          variant: "TEXTURE",
          hardener_id: "345-55",
          hardener_article_no: "800072",
          base_to_hardener_ratio: 5,
          water_pct: 0.10,
          mixing_order: ["base", "hardener", "water"],
        },
        "346-65:TOPCOAT": {
          system: "346-65",
          variant: "TOPCOAT",
          hardener_id: "345-19",
          hardener_article_no: "800071",
          base_to_hardener_ratio: 4,
          water_pct: 0.20,
          mixing_order: ["base", "hardener", "water"],
        },
        "346-65:TEXTURE": {
          system: "346-65",
          variant: "TEXTURE",
          hardener_id: "345-19",
          hardener_article_no: "800071",
          base_to_hardener_ratio: 4,
          water_pct: 0.10,
          mixing_order: ["base", "hardener", "water"],
        },
        "346-57:TOPCOAT": {
          system: "346-57",
          variant: "TOPCOAT",
          hardener_id: "345-57",
          hardener_article_no: "800050",
          base_to_hardener_ratio: 6,
          water_pct: 0.20,
          mixing_order: ["base", "water", "hardener"],
        },
        "346-57:TEXTURE": {
          system: "346-57",
          variant: "TEXTURE",
          hardener_id: "345-57",
          hardener_article_no: "800050",
          base_to_hardener_ratio: 6,
          water_pct: 0.10,
          mixing_order: ["base", "water", "hardener"],
        },
      };

      const SYSTEM_DISPLAY = {
        "346-55": {
          family: "MANKIEWICZ 346-55",
          base: {
            TOPCOAT: "ALEXIT Top Coat 346-55",
            TEXTURE: "ALEXIT Top Coat 346-55",
          },
        },
        "346-56": {
          family: "MANKIEWICZ BioProtect 346-56",
          base: {
            TOPCOAT: "ALEXIT Top Coat 346-56",
            TEXTURE: "ALEXIT Top Coat 346-56",
          },
        },
        "346-57": {
          family: "MANKIEWICZ 346-57",
          base: {
            TOPCOAT: "BASE 346-57",
            TEXTURE: "BASE 346-57",
          },
        },
        "346-65": {
          family: "MANKIEWICZ 346-65",
          base: {
            TOPCOAT: "ALEXIT FST 346-65",
            TEXTURE: "ALEXIT FST Strukturlack 346-65",
          },
        },
      };

      const HARDENER_COPY = {
        "345-55": "ALEXIT-Härter / Hardener 345-55",
        "345-19": "ALEXIT-Härter / Hardener 345-19",
        "345-57": "ALEXIT-Hardener 345-57",
      };

      const BARCODE_MAP = {
        "0032": {
          barcode: "3000000000076",
          batch_code: "0032",
          role: "base",
          article_id: 1,
          batch_id: 7,
          article_no: "800074",
          article_barcode: "2000000000015",
          system: "346-55",
          variant: "TOPCOAT",
        },
        "0033": {
          barcode: "3000000000083",
          batch_code: "0033",
          role: "base",
          article_id: 1,
          batch_id: 8,
          article_no: "800074",
          article_barcode: "2000000000015",
          system: "346-55",
          variant: "TOPCOAT",
        },
        "0567": {
          barcode: "3000000000090",
          batch_code: "0567",
          role: "base",
          article_id: 2,
          batch_id: 9,
          article_no: "800493",
          article_barcode: "2000000000022",
          system: "346-56",
          variant: "TOPCOAT",
        },
        "0568": {
          barcode: "3000000000106",
          batch_code: "0568",
          role: "base",
          article_id: 2,
          batch_id: 10,
          article_no: "800493",
          article_barcode: "2000000000022",
          system: "346-56",
          variant: "TOPCOAT",
        },
        "0002": {
          barcode: "3000000000113",
          batch_code: "0002",
          role: "base",
          article_id: 3,
          batch_id: 11,
          article_no: "800738",
          article_barcode: "2000000000039",
          system: "346-65",
          variant: "TOPCOAT",
        },
        "0156": {
          barcode: "3000000000014",
          batch_code: "0156",
          role: "base",
          article_id: 4,
          batch_id: 1,
          article_no: "800048",
          article_barcode: "2000000000046",
          system: "346-57",
          variant: "TOPCOAT",
        },
        "0158": {
          barcode: "3000000000021",
          batch_code: "0158",
          role: "base",
          article_id: 4,
          batch_id: 2,
          article_no: "800048",
          article_barcode: "2000000000046",
          system: "346-57",
          variant: "TOPCOAT",
        },
        "3217": {
          barcode: "3000000000052",
          batch_code: "3217",
          role: "hardener",
          article_id: 5,
          batch_id: 5,
          article_no: "800072",
          article_barcode: "2000000000053",
          hardener_id: "345-55",
        },
        "6644": {
          barcode: "3000000000069",
          batch_code: "6644",
          role: "hardener",
          article_id: 5,
          batch_id: 6,
          article_no: "800072",
          article_barcode: "2000000000053",
          hardener_id: "345-55",
        },
        "4567": {
          barcode: "3000000000045",
          batch_code: "4567",
          role: "hardener",
          article_id: 6,
          batch_id: 4,
          article_no: "800071",
          article_barcode: "2000000000060",
          hardener_id: "345-19",
        },
        "1984": {
          barcode: "3000000000038",
          batch_code: "1984",
          role: "hardener",
          article_id: 7,
          batch_id: 3,
          article_no: "800050",
          article_barcode: "2000000000077",
          hardener_id: "345-57",
        },
      };

      const ARTICLE_COPY = {
        "800074": "ALEXIT-FST-Topcoat 346-55",
        "800493": "ALEXIT-FST BioProtect 346-56",
        "800738": "ALEXIT-FST Strukturlack 346-65",
        "800048": "ALEXIT-FST-Topcoat 346-57",
        "800072": "ALEXIT-Härter / Hardener 345-55",
        "800071": "ALEXIT-Härter / Hardener 345-19",
        "800050": "ALEXIT-Hardener 345-57",
      };

      const BASE_SHORTCUTS = Object.values(BARCODE_MAP)
        .filter((entry) => entry.role === "base")
        .sort((left, right) => {
          if (left.article_no !== right.article_no) {
            return left.article_no.localeCompare(right.article_no);
          }
          return left.batch_code.localeCompare(right.batch_code);
        });

      const HARDENER_SHORTCUTS = Object.values(BARCODE_MAP)
        .filter((entry) => entry.role === "hardener")
        .sort((left, right) => {
          if (left.article_no !== right.article_no) {
            return left.article_no.localeCompare(right.article_no);
          }
          return left.batch_code.localeCompare(right.batch_code);
        });

      const INITIAL_STATE = () => ({
        connectionStatus: "connecting",
        accessToken: null,
        selectedVariant: DEFAULT_VARIANT,
        phase: "IDLE",
        scaleGrams: 0,
        scaleStable: true,
        lastScanned: "",
        inlineError: "",
        warning: null,
        successMessage: "",
        session: {
          system: null,
          variant: null,
          config: null,
          baseEntry: null,
          hardenerEntry: null,
          baseGrams: null,
          hardenerExpectedGrams: null,
          hardenerActualGrams: null,
          waterExpectedGrams: null,
          waterActualGrams: null,
          submissionPrefix: null,
          baseSubmitted: false,
          hardenerSubmitted: false,
          submissionError: "",
        },
      });

      const state = INITIAL_STATE();
      const dom = {};
      let animationInterval = null;
      let settleTimeout = null;
      let stableTimeout = null;
      let countdownInterval = null;
      let focusInterval = null;

      document.addEventListener("DOMContentLoaded", () => {
        cacheDom();
        renderShortcutButtons();
        bindEvents();
        render();
        keepScannerFocused();
        void loginDemo();
      });

      function cacheDom() {
        dom.connectionDot = document.getElementById("connection-dot");
        dom.connectionText = document.getElementById("connection-text");
        dom.systemBadge = document.getElementById("system-badge");
        dom.variantBadge = document.getElementById("variant-badge");
        dom.variantTopcoatButton = document.getElementById("variant-topcoat-button");
        dom.variantTextureButton = document.getElementById("variant-texture-button");
        dom.scaleValue = document.getElementById("scale-value");
        dom.stabilityDot = document.getElementById("stability-dot");
        dom.stabilityText = document.getElementById("stability-text");
        dom.stepPanel = document.getElementById("step-panel");
        dom.instructionText = document.getElementById("instruction-text");
        dom.instructionMeta = document.getElementById("instruction-meta");
        dom.countdown = document.getElementById("countdown");
        dom.feedback = document.getElementById("feedback");
        dom.breakdownPanel = document.getElementById("breakdown-panel");
        dom.baseDetail = document.getElementById("base-detail");
        dom.baseMeta = document.getElementById("base-meta");
        dom.baseStatus = document.getElementById("base-status");
        dom.hardenerDetail = document.getElementById("hardener-detail");
        dom.hardenerMeta = document.getElementById("hardener-meta");
        dom.hardenerStatus = document.getElementById("hardener-status");
        dom.waterDetail = document.getElementById("water-detail");
        dom.waterMeta = document.getElementById("water-meta");
        dom.waterStatus = document.getElementById("water-status");
        dom.scannerForm = document.getElementById("scanner-form");
        dom.scannerInput = document.getElementById("scanner-input");
        dom.lastScanned = document.getElementById("last-scanned");
        dom.baseShortcuts = document.getElementById("base-shortcuts");
        dom.hardenerShortcuts = document.getElementById("hardener-shortcuts");
        dom.weightBaseShortcut = document.getElementById("weight-base-shortcut");
        dom.weightHardenerShortcut = document.getElementById("weight-hardener-shortcut");
        dom.weightHardenerOutShortcut = document.getElementById("weight-hardener-out-shortcut");
        dom.weightWaterShortcut = document.getElementById("weight-water-shortcut");
        dom.weightResetShortcut = document.getElementById("weight-reset-shortcut");
        dom.sessionBase = document.getElementById("session-base");
        dom.sessionBaseBatch = document.getElementById("session-base-batch");
        dom.sessionHardener = document.getElementById("session-hardener");
        dom.sessionHardenerBatch = document.getElementById("session-hardener-batch");
        dom.sessionOrder = document.getElementById("session-order");
        dom.sessionNote = document.getElementById("session-note");
        dom.pourButton = document.getElementById("pour-button");
        dom.tareButton = document.getElementById("tare-button");
        dom.retryButton = document.getElementById("retry-button");
        dom.overrideButton = document.getElementById("override-button");
        dom.newMixButton = document.getElementById("new-mix-button");
      }

      function renderShortcutButtons() {
        dom.baseShortcuts.innerHTML = BASE_SHORTCUTS.map((entry) => {
          return `
            <button
              type="button"
              class="shortcut-btn shortcut-btn-base"
              data-scan-value="${entry.barcode}"
            >
              <span class="shortcut-primary">${entry.article_no} / ${entry.batch_code}</span>
              <span class="shortcut-secondary">${getSystemDisplayLabel(entry.system)} • ${getBaseDisplayName(entry, state.selectedVariant)}</span>
            </button>
          `;
        }).join("");

        dom.hardenerShortcuts.innerHTML = HARDENER_SHORTCUTS.map((entry) => {
          const supportedSystems = getSystemsForHardener(entry.hardener_id).join(" / ");
          return `
            <button
              type="button"
              class="shortcut-btn shortcut-btn-hardener"
              data-scan-value="${entry.barcode}"
            >
              <span class="shortcut-primary">${entry.article_no} / ${entry.batch_code}</span>
              <span class="shortcut-secondary">${getHardenerDisplayName(entry)} • za ${supportedSystems}</span>
            </button>
          `;
        }).join("");
      }

      function bindEvents() {
        dom.scannerForm.addEventListener("submit", (event) => {
          event.preventDefault();
          const value = dom.scannerInput.value.trim();
          dom.scannerInput.value = "";
          handleScan(value);
        });

        dom.baseShortcuts.addEventListener("click", (event) => {
          const button = event.target.closest("[data-scan-value]");
          if (!button) {
            return;
          }
          handleShortcutScan(button.getAttribute("data-scan-value") || "");
        });

        dom.hardenerShortcuts.addEventListener("click", (event) => {
          const button = event.target.closest("[data-scan-value]");
          if (!button) {
            return;
          }
          handleShortcutScan(button.getAttribute("data-scan-value") || "");
        });

        dom.weightBaseShortcut.addEventListener("click", () => {
          applyWeightShortcut("base");
        });
        dom.weightHardenerShortcut.addEventListener("click", () => {
          applyWeightShortcut("hardener");
        });
        dom.weightHardenerOutShortcut.addEventListener("click", () => {
          applyWeightShortcut("hardener_out");
        });
        dom.weightWaterShortcut.addEventListener("click", () => {
          applyWeightShortcut("water");
        });
        dom.weightResetShortcut.addEventListener("click", () => {
          applyWeightShortcut("reset");
        });
        dom.variantTopcoatButton.addEventListener("click", () => {
          handleVariantChange("TOPCOAT");
        });
        dom.variantTextureButton.addEventListener("click", () => {
          handleVariantChange("TEXTURE");
        });

        dom.pourButton.addEventListener("click", () => {
          void handlePour();
        });
        dom.tareButton.addEventListener("click", () => {
          handleTare();
        });
        dom.retryButton.addEventListener("click", () => {
          void handleRetry();
        });
        dom.overrideButton.addEventListener("click", () => {
          handleToleranceOverride();
        });
        dom.newMixButton.addEventListener("click", () => {
          resetForNewMix();
        });
        window.addEventListener("click", () => focusScannerSoon());
        window.addEventListener("keydown", () => focusScannerSoon());
      }

      function handleVariantChange(nextVariant) {
        if (state.selectedVariant === nextVariant) {
          return;
        }

        if (!["IDLE", "WAITING_BASE_SCAN"].includes(state.phase)) {
          state.inlineError = "Varijantu promijenite prije skeniranja baze za aktivnu mješavinu.";
          render();
          return;
        }

        clearMessages({ keepSuccess: true });
        state.selectedVariant = nextVariant;
        renderShortcutButtons();
        render();
      }

      async function loginDemo() {
        setConnection("connecting", "Povezivanje na STOQIO...");
        try {
          const response = await apiRequest("/auth/login", {
            method: "POST",
            auth: false,
            body: {
              username: DEMO_CONFIG.demo_username,
              password: DEMO_CONFIG.demo_password,
            },
          });
          state.accessToken = response.access_token;
          setConnection("ok", `Spojeno kao ${response.user.username}`);
        } catch (error) {
          state.inlineError = "Greška konfiguracije — provjeri DEMO_CONFIG";
          setConnection("error", "Login nije uspio");
          render();
        }
      }

      function setConnection(status, label) {
        state.connectionStatus = status;
        dom.connectionText.textContent = label;
        dom.connectionDot.className =
          "dot " +
          (status === "ok" ? "dot-ok" : status === "error" ? "dot-error" : "dot-connecting");
      }

      async function apiRequest(path, options = {}) {
        const { method = "GET", body, auth = true } = options;
        const headers = {
          "Accept-Language": "hr",
          Accept: "application/json",
        };
        if (body !== undefined) {
          headers["Content-Type"] = "application/json";
        }
        if (auth && state.accessToken) {
          headers.Authorization = `Bearer ${state.accessToken}`;
        }

        const response = await fetch(`${DEMO_CONFIG.stoqio_base_url}${path}`, {
          method,
          headers,
          body: body === undefined ? undefined : JSON.stringify(body),
        });

        const raw = await response.text();
        let payload = null;
        try {
          payload = raw ? JSON.parse(raw) : null;
        } catch (_error) {
          payload = null;
        }

        if (!response.ok) {
          const message =
            payload?.message ||
            payload?.error ||
            `HTTP ${response.status}`;
          throw new Error(message);
        }

        return payload;
      }

      function keepScannerFocused() {
        clearInterval(focusInterval);
        focusInterval = window.setInterval(() => {
          if (document.activeElement !== dom.scannerInput) {
            dom.scannerInput.focus({ preventScroll: true });
          }
        }, 800);
      }

      function focusScannerSoon() {
        window.setTimeout(() => {
          dom.scannerInput.focus({ preventScroll: true });
        }, 0);
      }

      function handleShortcutScan(value) {
        if (!value) {
          return;
        }
        dom.scannerInput.value = value;
        if (!isScannerActivePhase()) {
          state.lastScanned = value;
          state.inlineError = "Skeniranje je aktivno tek nakon očitanja vage za trenutni korak.";
          render();
          focusScannerSoon();
          return;
        }
        dom.scannerInput.value = "";
        handleScan(value);
        focusScannerSoon();
      }

      function handleScan(value) {
        state.lastScanned = value;
        if (!value) {
          render();
          return;
        }

        if (!isScannerActivePhase()) {
          render();
          return;
        }

        clearMessages({ keepSuccess: true });

        if (state.phase === "WAITING_BASE_SCAN") {
          processBaseScan(value);
          return;
        }

        if (state.phase === "WAITING_HARDENER_SCAN") {
          processHardenerScan(value);
          return;
        }
      }

      function isScannerActivePhase() {
        return state.phase === "WAITING_BASE_SCAN" || state.phase === "WAITING_HARDENER_SCAN";
      }

      function resolveScanEntry(scanValue) {
        const normalized = scanValue.trim();
        if (BARCODE_MAP[normalized]) {
          return BARCODE_MAP[normalized];
        }
        return Object.values(BARCODE_MAP).find((entry) => entry.barcode === normalized) || null;
      }

      function processBaseScan(scanValue) {
        const entry = resolveScanEntry(scanValue);
        if (!entry) {
          state.inlineError = "Nepoznati barkod";
          render();
          return;
        }
        if (entry.role !== "base") {
          state.inlineError = "Skenirajte boju, ne učvršćivač";
          render();
          return;
        }

        const selectedVariant = state.selectedVariant || DEFAULT_VARIANT;
        const config = MIXING_SYSTEMS[`${entry.system}:${selectedVariant}`];
        if (!config) {
          state.inlineError = "Konfiguracija sustava nije pronađena.";
          render();
          return;
        }

        state.session.baseEntry = entry;
        state.session.config = config;
        state.session.system = entry.system;
        state.session.variant = selectedVariant;
        state.session.baseGrams = state.scaleGrams;
        state.session.hardenerExpectedGrams = roundToOne(state.session.baseGrams / config.base_to_hardener_ratio);
        state.session.waterExpectedGrams = roundToOne(state.session.baseGrams * config.water_pct);
        state.phase = "TARE_AFTER_BASE";
        render();
      }

      function processHardenerScan(scanValue) {
        const entry = resolveScanEntry(scanValue);
        if (!entry) {
          state.inlineError = "Nepoznati barkod";
          render();
          return;
        }
        if (entry.role !== "hardener") {
          state.inlineError = "Skenirajte učvršćivač, ne boju";
          render();
          return;
        }
        if (entry.hardener_id !== state.session.config.hardener_id) {
          state.inlineError = "Pogrešan učvršćivač za ovaj sustav boje";
          render();
          return;
        }

        state.session.hardenerEntry = entry;
        state.session.hardenerActualGrams = state.scaleGrams;

        const expected = state.session.hardenerExpectedGrams;
        const actual = state.session.hardenerActualGrams;
        const min = expected * (1 - DEMO_CONFIG.hardener_tolerance_pct);
        const max = expected * (1 + DEMO_CONFIG.hardener_tolerance_pct);

        if (actual < min || actual > max) {
          state.phase = "HARDENER_WARNING";
          state.warning = {
            expected,
            actual,
            diff: roundToOne(actual - expected),
          };
          render();
          return;
        }

        proceedAfterHardener();
      }

      function proceedAfterHardener() {
        state.warning = null;
        if (state.session.config.mixing_order[1] === "water") {
          enterConfirming();
        } else {
          state.phase = "POURING_WATER_LAST";
        }
        render();
      }

      function applyWeightShortcut(mode) {
        clearScaleTimers();
        clearInterval(countdownInterval);
        countdownInterval = null;
        clearMessages({ keepSuccess: true });

        if (mode === "reset") {
          state.scaleGrams = 0;
          state.scaleStable = true;
          render();
          return;
        }

        if (mode === "base") {
          if (!["IDLE", "WAITING_BASE_SCAN"].includes(state.phase)) {
            state.inlineError = "Bazu simuliraj na početku miješanja.";
            render();
            return;
          }
          applyStableReading({
            grams: roundToOne(randomBetween(
              DEMO_CONFIG.scale.base_range_grams.min,
              DEMO_CONFIG.scale.base_range_grams.max
            )),
            nextPhase: "WAITING_BASE_SCAN",
          });
          return;
        }

        if (mode === "hardener" || mode === "hardener_out") {
          if (!state.session.config || state.session.hardenerExpectedGrams == null) {
            state.inlineError = "Prvo skeniraj bazu da demo zna očekivani učvršćivač.";
            render();
            return;
          }
          if (!["POURING_HARDENER", "WAITING_HARDENER_SCAN", "HARDENER_WARNING"].includes(state.phase)) {
            state.inlineError = "Učvršćivač simuliraj tek kad dođe red na učvršćivač.";
            render();
            return;
          }

          const expected = state.session.hardenerExpectedGrams;
          const grams =
            mode === "hardener"
              ? roundToOne(withVariance(expected))
              : roundToOne(expected * 1.22);

          state.warning = null;
          applyStableReading({
            grams,
            nextPhase: "WAITING_HARDENER_SCAN",
          });
          return;
        }

        if (mode === "water") {
          if (!state.session.config || state.session.waterExpectedGrams == null) {
            state.inlineError = "Prvo skeniraj bazu da demo izračuna vodu.";
            render();
            return;
          }
          if (!["POURING_WATER_FIRST", "POURING_WATER_LAST"].includes(state.phase)) {
            state.inlineError = "Vodu simuliraj tek kad dođe red na vodu.";
            render();
            return;
          }

          const grams = roundToOne(withVariance(state.session.waterExpectedGrams));
          const nextPhase = state.phase === "POURING_WATER_FIRST" ? "TARE_AFTER_WATER" : "CONFIRMING";
          applyStableReading({
            grams,
            nextPhase,
            acceptAs: "water",
          });
        }
      }

      function applyStableReading({ grams, nextPhase, acceptAs = null }) {
        state.scaleStable = true;
        state.scaleGrams = grams;
        if (acceptAs === "water") {
          state.session.waterActualGrams = grams;
        }
        state.phase = nextPhase;
        if (nextPhase === "CONFIRMING") {
          enterConfirming();
          return;
        }
        render();
      }

      async function handlePour() {
        if (state.connectionStatus !== "ok") {
          state.inlineError = "Demo nije prijavljen na STOQIO API.";
          render();
          return;
        }

        clearMessages({ keepSuccess: false });

        if (state.phase === "IDLE") {
          simulatePour({
            min: DEMO_CONFIG.scale.base_range_grams.min,
            max: DEMO_CONFIG.scale.base_range_grams.max,
            nextPhase: "WAITING_BASE_SCAN",
          });
          return;
        }

        if (state.phase === "POURING_WATER_FIRST") {
          const target = roundToOne(withVariance(state.session.waterExpectedGrams));
          simulatePour({ min: target, max: target, nextPhase: "TARE_AFTER_WATER", acceptAs: "water" });
          return;
        }

        if (state.phase === "POURING_HARDENER") {
          const target = roundToOne(withVariance(state.session.hardenerExpectedGrams));
          simulatePour({ min: target, max: target, nextPhase: "WAITING_HARDENER_SCAN" });
          return;
        }

        if (state.phase === "POURING_WATER_LAST") {
          const target = roundToOne(withVariance(state.session.waterExpectedGrams));
          simulatePour({ min: target, max: target, nextPhase: "CONFIRMING", acceptAs: "water" });
        }
      }

      function simulatePour({ min, max, nextPhase, acceptAs = null }) {
        clearScaleTimers();
        state.scaleStable = false;
        state.scaleGrams = 0;
        render();

        const target = roundToOne(randomBetween(min, max));
        let current = 0;

        animationInterval = window.setInterval(() => {
          const remaining = target - current;
          if (remaining <= 4) {
            clearInterval(animationInterval);
            animationInterval = null;
            settleTimeout = window.setTimeout(() => {
              state.scaleGrams = target;
              render();
              stableTimeout = window.setTimeout(() => {
                state.scaleStable = true;
                if (acceptAs === "water") {
                  state.session.waterActualGrams = target;
                }
                state.phase = nextPhase;
                if (nextPhase === "CONFIRMING") {
                  enterConfirming();
                  return;
                }
                render();
              }, DEMO_CONFIG.scale.stability_window_seconds * 1000);
            }, 700);
            return;
          }

          const step = Math.min(remaining, randomBetween(remaining * 0.08, remaining * 0.24));
          current = roundToOne(current + step);
          state.scaleGrams = current;
          render();
        }, 130);
      }

      function clearScaleTimers() {
        clearInterval(animationInterval);
        clearTimeout(settleTimeout);
        clearTimeout(stableTimeout);
        animationInterval = null;
        settleTimeout = null;
        stableTimeout = null;
      }

      function handleTare() {
        clearMessages({ keepSuccess: true });
        state.scaleGrams = 0;
        state.scaleStable = true;

        if (state.phase === "TARE_AFTER_BASE") {
          state.phase =
            state.session.config.mixing_order[1] === "water"
              ? "POURING_WATER_FIRST"
              : "POURING_HARDENER";
          render();
          return;
        }

        if (state.phase === "TARE_AFTER_WATER") {
          state.phase = "POURING_HARDENER";
          render();
        }
      }

      function handleToleranceOverride() {
        if (state.phase !== "HARDENER_WARNING") {
          return;
        }
        proceedAfterHardener();
      }

      async function handleRetry() {
        if (state.phase === "HARDENER_WARNING") {
          state.warning = null;
          state.session.hardenerEntry = null;
          state.session.hardenerActualGrams = null;
          state.scaleGrams = 0;
          state.scaleStable = true;
          state.phase = "POURING_HARDENER";
          render();
          return;
        }

        if (state.phase === "ERROR") {
          await submitDrafts();
        }
      }

      function enterConfirming() {
        state.phase = "CONFIRMING";
        let remaining = DEMO_CONFIG.submit_countdown_seconds;
        render();
        dom.countdown.hidden = false;
        dom.countdown.textContent = `Automatsko slanje za ${remaining} s`;
        clearInterval(countdownInterval);
        countdownInterval = window.setInterval(async () => {
          remaining -= 1;
          if (remaining <= 0) {
            clearInterval(countdownInterval);
            countdownInterval = null;
            dom.countdown.textContent = "Slanje u STOQIO...";
            await submitDrafts();
            return;
          }
          dom.countdown.textContent = `Automatsko slanje za ${remaining} s`;
        }, 1000);
      }

      async function submitDrafts() {
        state.phase = "SUBMITTING";
        state.inlineError = "";
        render();

        const submissionPrefix =
          state.session.submissionPrefix ||
          (window.crypto && window.crypto.randomUUID
            ? window.crypto.randomUUID()
            : `demo-${Date.now()}-${Math.random().toString(16).slice(2)}`);
        state.session.submissionPrefix = submissionPrefix;

        try {
          if (!state.session.baseSubmitted) {
            await apiRequest("/drafts", {
              method: "POST",
              body: buildDraftPayload({
                entry: state.session.baseEntry,
                quantityGrams: state.session.baseGrams,
                clientEventId: `${submissionPrefix}-base`,
              }),
            });
            state.session.baseSubmitted = true;
          }

          if (!state.session.hardenerSubmitted) {
            await apiRequest("/drafts", {
              method: "POST",
              body: buildDraftPayload({
                entry: state.session.hardenerEntry,
                quantityGrams: state.session.hardenerActualGrams,
                clientEventId: `${submissionPrefix}-hardener`,
              }),
            });
            state.session.hardenerSubmitted = true;
          }

          state.successMessage = "Uspješno poslano u odobravanje";
          state.phase = "SUCCESS";
          render();
        } catch (error) {
          state.session.submissionError = String(error.message || error);
          state.inlineError = state.session.baseSubmitted
            ? `Baza je poslana, ali učvršćivač nije: ${state.session.submissionError}`
            : `Slanje nije uspjelo: ${state.session.submissionError}`;
          state.phase = "ERROR";
          render();
        }
      }

      function buildDraftPayload({ entry, quantityGrams, clientEventId }) {
        return {
          article_id: entry.article_id,
          batch_id: entry.batch_id,
          quantity: Number((quantityGrams / 1000).toFixed(4)),
          uom: "kg",
          source: "manual",
          client_event_id: clientEventId,
          draft_note: `Demo: ${state.session.system} ${state.session.variant}`,
        };
      }

      function resetForNewMix() {
        clearScaleTimers();
        clearInterval(countdownInterval);
        countdownInterval = null;
        const preservedToken = state.accessToken;
        const preservedConnection = state.connectionStatus;
        const preservedVariant = state.selectedVariant;
        Object.assign(state, INITIAL_STATE());
        state.accessToken = preservedToken;
        state.connectionStatus = preservedConnection;
        state.selectedVariant = preservedVariant;
        state.scaleStable = true;
        renderShortcutButtons();
        render();
      }

      function clearMessages({ keepSuccess }) {
        state.inlineError = "";
        state.warning = null;
        if (!keepSuccess) {
          state.successMessage = "";
        }
      }

      function render() {
        dom.scaleValue.textContent = formatGrams(state.scaleGrams);
        dom.lastScanned.textContent = state.lastScanned || "—";

        if (state.scaleStable) {
          dom.stabilityDot.className = "dot dot-ok";
          dom.stabilityText.textContent = state.scaleGrams === 0 ? "Spremno" : "Stabilno";
        } else {
          dom.stabilityDot.className = "dot dot-unstable";
          dom.stabilityText.textContent = "Nestabilno";
        }

        dom.systemBadge.hidden = !state.session.system;
        dom.variantBadge.hidden = !state.session.variant;
        dom.systemBadge.textContent = state.session.system || "";
        dom.variantBadge.textContent = state.session.variant || "";
        renderVariantButtons();

        dom.breakdownPanel.hidden = !state.session.config;
        renderBreakdown();
        renderFeedback();
        renderSessionSummary();
        renderButtons();
        renderCurrentInstruction();

        if (state.phase !== "CONFIRMING" && state.phase !== "SUBMITTING") {
          dom.countdown.hidden = true;
          dom.countdown.textContent = "";
        }
      }

      function renderVariantButtons() {
        const variantLocked = !["IDLE", "WAITING_BASE_SCAN"].includes(state.phase);

        dom.variantTopcoatButton.className =
          "variant-btn" + (state.selectedVariant === "TOPCOAT" ? " variant-btn-active" : "");
        dom.variantTextureButton.className =
          "variant-btn" + (state.selectedVariant === "TEXTURE" ? " variant-btn-active" : "");

        dom.variantTopcoatButton.disabled = variantLocked;
        dom.variantTextureButton.disabled = variantLocked;
      }

      function renderCurrentInstruction() {
        const instruction = currentInstructionContent();
        dom.instructionText.textContent = instruction.headline;
        dom.instructionMeta.textContent = instruction.meta || "";
        dom.instructionMeta.hidden = !instruction.meta;
        dom.stepPanel.classList.toggle("step-panel-attention", instruction.emphasis === true);
      }

      function renderBreakdown() {
        const baseLabel = state.session.baseEntry
          ? `${getBaseDisplayName(state.session.baseEntry, state.session.variant)} (${state.session.baseEntry.batch_code})`
          : "Nije još potvrđeno";
        dom.baseDetail.textContent = baseLabel;
        dom.baseMeta.textContent = state.session.baseGrams != null ? formatGrams(state.session.baseGrams) : "—";
        dom.baseStatus.textContent = state.session.baseGrams != null ? "✓ izmjereno" : "Na čekanju";
        dom.baseStatus.className =
          "status " + (state.session.baseGrams != null ? "status-done" : "status-info");

        const hardenerExpected =
          state.session.hardenerExpectedGrams != null
            ? `Plan: ${formatGrams(state.session.hardenerExpectedGrams)}`
            : "—";
        const hardenerActual =
          state.session.hardenerActualGrams != null
            ? ` | Izmjereno: ${formatGrams(state.session.hardenerActualGrams)}`
            : "";
        dom.hardenerMeta.textContent = `${hardenerExpected}${hardenerActual}`;
        dom.hardenerDetail.textContent = state.session.hardenerEntry
          ? `${getHardenerDisplayName(state.session.hardenerEntry)} (${state.session.hardenerEntry.batch_code})`
          : state.session.config
            ? `Očekivani učvršćivač: ${getHardenerDisplayName(state.session.config.hardener_id)}`
            : "Nije još potvrđeno";
        dom.hardenerStatus.textContent = hardenerStatusText();
        dom.hardenerStatus.className = "status " + hardenerStatusClass();

        dom.waterMeta.textContent =
          state.session.waterExpectedGrams != null
            ? `Plan: ${formatGrams(state.session.waterExpectedGrams)}${state.session.waterActualGrams != null ? ` | Izmjereno: ${formatGrams(state.session.waterActualGrams)}` : ""}`
            : "—";
        dom.waterDetail.textContent = "Informativno, ne šalje se u STOQIO";
        dom.waterStatus.textContent = waterStatusText();
        dom.waterStatus.className = "status " + waterStatusClass();
      }

      function renderFeedback() {
        dom.feedback.innerHTML = "";
        if (state.inlineError) {
          appendMessage("message message-error", state.inlineError);
        }
        if (state.warning) {
          appendMessage(
            "message message-warning",
            `Učvršćivač je izvan tolerancije. Očekivano: ${formatGrams(state.warning.expected)}, izmjereno: ${formatGrams(state.warning.actual)}, razlika: ${formatSignedGrams(state.warning.diff)}.`
          );
        }
        if (state.successMessage) {
          appendMessage("message message-success", `✓ ${state.successMessage}`);
        }
      }

      function appendMessage(className, text) {
        const node = document.createElement("div");
        node.className = className;
        node.textContent = text;
        dom.feedback.appendChild(node);
      }

      function renderSessionSummary() {
        dom.sessionBase.textContent = state.session.baseEntry
          ? `${getBaseDisplayName(state.session.baseEntry, state.session.variant)}`
          : "—";
        dom.sessionBaseBatch.textContent = state.session.baseEntry
          ? `${state.session.baseEntry.batch_code} / ${state.session.baseEntry.barcode}`
          : "—";
        dom.sessionHardener.textContent = state.session.hardenerEntry
          ? `${getHardenerDisplayName(state.session.hardenerEntry)}`
          : state.session.config
            ? `${getHardenerDisplayName(state.session.config.hardener_id)}`
            : "—";
        dom.sessionHardenerBatch.textContent = state.session.hardenerEntry
          ? `${state.session.hardenerEntry.batch_code} / ${state.session.hardenerEntry.barcode}`
          : "—";
        dom.sessionOrder.textContent = state.session.config
          ? state.session.config.mixing_order.join(" → ")
          : "—";
        dom.sessionNote.textContent = state.session.system
          ? `Demo: ${state.session.system} ${state.session.variant}`
          : "—";
      }

      function renderButtons() {
        dom.pourButton.hidden = !["IDLE", "POURING_WATER_FIRST", "POURING_HARDENER", "POURING_WATER_LAST"].includes(state.phase);
        dom.tareButton.hidden = !["TARE_AFTER_BASE", "TARE_AFTER_WATER"].includes(state.phase);
        dom.retryButton.hidden = !["HARDENER_WARNING", "ERROR"].includes(state.phase);
        dom.overrideButton.hidden = state.phase !== "HARDENER_WARNING";
        dom.newMixButton.hidden = state.phase !== "SUCCESS";

        dom.pourButton.textContent = pourButtonLabel();
      }

      function pourButtonLabel() {
        if (state.phase === "POURING_WATER_FIRST" || state.phase === "POURING_WATER_LAST") {
          return "Ulij vodu";
        }
        if (state.phase === "POURING_HARDENER") {
          return "Ulij učvršćivač";
        }
        return "Ulij bazu";
      }

      function currentInstructionContent() {
        const activeVariant = state.session.variant || state.selectedVariant;
        const hardenerCode = state.session.config?.hardener_id || "učvršćivač";
        const hardenerName = getHardenerDisplayName(state.session.config?.hardener_id);
        const baseName = state.session.baseEntry
          ? getBaseDisplayName(state.session.baseEntry, state.session.variant)
          : "bazu";

        switch (state.phase) {
          case "IDLE":
            return {
              headline: "Odaberite varijantu i ulijte bazu",
              meta: `Aktivna varijanta: ${activeVariant}. Omjer vode za recepturu zaključava se nakon skeniranja baze.`,
            };
          case "WAITING_BASE_SCAN":
            return {
              headline: "Skenirajte barkod baze",
              meta: `${formatGrams(state.scaleGrams)} na vagi • varijanta ${activeVariant}`,
            };
          case "TARE_AFTER_BASE":
            return {
              headline: "Tarirajte vagu",
              meta: `${baseName} potvrđena • ${formatGrams(state.session.baseGrams)}`,
            };
          case "POURING_WATER_FIRST":
            return {
              headline: `Ulijte ${formatGrams(state.session.waterExpectedGrams)} vode`,
              meta: "Za sustav 346-57 voda ide prije učvršćivača.",
              emphasis: true,
            };
          case "TARE_AFTER_WATER":
            return {
              headline: "Tarirajte vagu",
              meta: `${formatGrams(state.session.waterActualGrams)} vode prihvaćeno • sljedeći korak je učvršćivač`,
            };
          case "POURING_HARDENER":
            return {
              headline: `Ulijte ${formatGrams(state.session.hardenerExpectedGrams)} učvršćivača ${hardenerCode}`,
              meta: hardenerName,
              emphasis: true,
            };
          case "WAITING_HARDENER_SCAN":
            return {
              headline: `Skenirajte učvršćivač ${hardenerCode}`,
              meta: `${hardenerName} • planirana količina ${formatGrams(state.session.hardenerExpectedGrams)}`,
            };
          case "HARDENER_WARNING":
            return {
              headline: `Provjerite količinu učvršćivača ${hardenerCode}`,
              meta: `Plan ${formatGrams(state.warning?.expected)} • izmjereno ${formatGrams(state.warning?.actual)} • dopušteno odstupanje ±10%`,
            };
          case "POURING_WATER_LAST":
            return {
              headline: `Ulijte ${formatGrams(state.session.waterExpectedGrams)} vode`,
              meta: "Voda je informativna i ne šalje se u STOQIO.",
              emphasis: true,
            };
          case "CONFIRMING":
            return {
              headline: "Provjera završena",
              meta: `Slanje u odobravanje za ${state.session.system} ${state.session.variant} kreće automatski.`,
            };
          case "SUBMITTING":
            return {
              headline: "Šaljem draftove u STOQIO...",
              meta: `Šalju se baza i učvršćivač za ${state.session.system} ${state.session.variant}.`,
            };
          case "SUCCESS":
            return {
              headline: "Uspješno poslano u odobravanje",
              meta: `Možete pokrenuti novo miješanje za istu ili drugu varijantu.`,
            };
          case "ERROR":
            return {
              headline: "Slanje nije završilo",
              meta: "Provjerite poruku ispod i pokušajte ponovno.",
            };
          default:
            return {
              headline: "Ulijte bazu u posudu za miješanje",
              meta: "",
            };
        }
      }

      function hardenerStatusText() {
        if (state.session.hardenerActualGrams != null && state.warning == null) {
          return "✓ potvrđeno";
        }
        if (state.phase === "POURING_HARDENER" || state.phase === "WAITING_HARDENER_SCAN" || state.phase === "HARDENER_WARNING") {
          return "→ ulijte sada";
        }
        return "Na čekanju";
      }

      function hardenerStatusClass() {
        if (state.session.hardenerActualGrams != null && state.warning == null) {
          return "status-done";
        }
        if (state.phase === "POURING_HARDENER" || state.phase === "WAITING_HARDENER_SCAN" || state.phase === "HARDENER_WARNING") {
          return "status-active";
        }
        return "status-info";
      }

      function waterStatusText() {
        if (state.session.waterActualGrams != null) {
          return "✓ prihvaćeno";
        }
        if (state.phase === "POURING_WATER_FIRST" || state.phase === "POURING_WATER_LAST") {
          return "→ ulijte sada";
        }
        if (state.session.waterExpectedGrams != null) {
          return "ℹ poslije";
        }
        return "Na čekanju";
      }

      function waterStatusClass() {
        if (state.session.waterActualGrams != null) {
          return "status-done";
        }
        if (state.phase === "POURING_WATER_FIRST" || state.phase === "POURING_WATER_LAST") {
          return "status-active";
        }
        return "status-info";
      }

      function getSystemDisplayLabel(systemCode) {
        return SYSTEM_DISPLAY[systemCode]?.family || `Sustav ${systemCode}`;
      }

      function getBaseDisplayName(entry, variant) {
        if (!entry) {
          return "Baza";
        }

        const resolvedVariant = variant || state.session.variant || state.selectedVariant || DEFAULT_VARIANT;
        return (
          SYSTEM_DISPLAY[entry.system]?.base?.[resolvedVariant] ||
          ARTICLE_COPY[entry.article_no] ||
          `${entry.article_no}`
        );
      }

      function getHardenerDisplayName(entryOrId) {
        const hardenerId =
          typeof entryOrId === "string"
            ? entryOrId
            : entryOrId?.hardener_id || null;

        if (hardenerId && HARDENER_COPY[hardenerId]) {
          return HARDENER_COPY[hardenerId];
        }

        if (typeof entryOrId !== "string" && entryOrId?.article_no && ARTICLE_COPY[entryOrId.article_no]) {
          return ARTICLE_COPY[entryOrId.article_no];
        }

        return hardenerId || "Učvršćivač";
      }

      function getSystemsForHardener(hardenerId) {
        return Array.from(
          new Set(
            Object.values(MIXING_SYSTEMS)
              .filter((config) => config.hardener_id === hardenerId)
              .map((config) => config.system)
          )
        ).sort();
      }

      function formatGrams(value) {
        return `${Number(value || 0).toFixed(1).replace(".", ",")} g`;
      }

      function formatSignedGrams(value) {
        const numeric = Number(value || 0);
        return `${numeric > 0 ? "+" : ""}${numeric.toFixed(1).replace(".", ",")} g`;
      }

      function roundToOne(value) {
        return Number(Number(value).toFixed(1));
      }

      function randomBetween(min, max) {
        return Math.random() * (max - min) + min;
      }

      function withVariance(baseValue) {
        return baseValue * randomBetween(0.95, 1.05);
      }
