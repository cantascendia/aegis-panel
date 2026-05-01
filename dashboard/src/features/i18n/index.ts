import dayjs from 'dayjs';
import i18n from 'i18next';
import "dayjs/locale/fa";
import "dayjs/locale/ru";
import "dayjs/locale/zh-cn";
import "dayjs/locale/ar";
import LanguageDetector from 'i18next-browser-languagedetector';
import HttpApi from 'i18next-http-backend';
import { initReactI18next } from 'react-i18next';

declare module 'i18next' {
    interface CustomTypeOptions {
        returnNull: false;
    }
}

i18n
    .use(LanguageDetector)
    .use(HttpApi)
    .use(initReactI18next)
    .init({
        debug: process.env.NODE_ENV === 'development',
        fallbackLng: 'en',
        interpolation: {
            escapeValue: false,
        },
        react: {
            useSuspense: false,
        },
        // load: 'currentOnly' keeps the region suffix so 'zh-cn' requests
        // /locales/zh-cn.json. Earlier 'languageOnly' truncated to 'zh' which
        // 404'd because the file is named zh-cn.json — clicking 简体中文 in
        // the LanguageSwitchMenu silently fell back to fallbackLng='en'.
        load: 'currentOnly',
        detection: {
            order: ['localStorage', 'sessionStorage', 'cookie', 'navigator'],
            // caches tells i18next-browser-languagedetector which storages to
            // PERSIST the chosen language to. Without this the choice is lost
            // on every page reload.
            caches: ['localStorage'],
        },
        backend: {
            loadPath: `/locales/{{lng}}.json`,
        },
        supportedLngs: ['en', 'kur', 'kmr', 'ckb', 'fa', 'ru', 'ar', 'zh-cn'],
    })
    .then(() => {
        dayjs.locale(i18n.language);
        document.documentElement.lang = i18n.language;
    });

i18n.on('languageChanged', (lng) => {
    dayjs.locale(lng);
    document.documentElement.lang = lng;
});

export default i18n;
