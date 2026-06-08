export const translations = {
  en: {
    nav: {
      globalMap: "Global Map",
      militaryIntel: "Military Intel",
      intelRepository: "Intel Repository",
      dailySynthesis: "Daily Synthesis",
      scenarioEngine: "Scenario Engine",
      secureIntake: "Secure Intake",
      commandCenter: "Command Center",
    },
    dashboard: {
      title: "Global Overview",
      subtitle: "Real-time intelligence nodes",
      intelItems: "INTEL ITEMS",
      pending: "PENDING",
    },
    military: {
      title: "Military Intelligence",
      subtitle: "Weapon systems, transfers, and strategic assets",
      weapons: "Weapons",
      transfers: "Arms Transfers",
      bases: "Military Bases",
      budgets: "Defense Budgets",
    },
    common: {
      loading: "Loading...",
      error: "Error",
      retry: "Retry",
      search: "Search",
      filter: "Filter",
    },
  },
  es: {
    nav: {
      globalMap: "Mapa Global",
      militaryIntel: "Intel Militar",
      intelRepository: "Repositorio Intel",
      dailySynthesis: "Síntesis Diaria",
      scenarioEngine: "Motor de Escenarios",
      secureIntake: "Intake Seguro",
      commandCenter: "Centro de Mando",
    },
    dashboard: {
      title: "Vista Global",
      subtitle: "Nodos de inteligencia en tiempo real",
      intelItems: "ELEMENTOS INTEL",
      pending: "PENDIENTES",
    },
    military: {
      title: "Inteligencia Militar",
      subtitle: "Sistemas de armas, transferencias y activos estratégicos",
      weapons: "Armas",
      transfers: "Transferencias de Armas",
      bases: "Bases Militares",
      budgets: "Presupuestos de Defensa",
    },
    common: {
      loading: "Cargando...",
      error: "Error",
      retry: "Reintentar",
      search: "Buscar",
      filter: "Filtrar",
    },
  },
};

export type Locale = keyof typeof translations;
export type TranslationKeys = typeof translations.en;

export function getTranslations(locale: Locale = 'en'): TranslationKeys {
  return translations[locale];
}
