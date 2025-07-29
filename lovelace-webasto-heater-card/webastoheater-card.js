/*
* This is a Lovelace custom card for Webasto Heater.
*
* @package custom-cards/lovelace-webasto-heater-card
* @file webastoheater-card.js
* @author ewgen198409
* @license MIT
*/
import { LitElement, html, css } from 'https://unpkg.com/lit-element@2.4.0/lit-element.js?module';
import { styleMap } from 'https://unpkg.com/lit-html/directives/style-map.js?module'; // Импорт для динамического применения стилей

// Класс WebastoHeaterCardEditor и его регистрация удалены.

class WebastoHeaterCard extends LitElement {
    static get properties() {
        return {
            hass: {},
            config: {},
            _entities: { type: Object },
            _activeTab: { type: String },
        };
    }

    constructor() {
        super();
        this._entities = {};
        this._activeTab = 'main';
    }

    setConfig(config) {
        // Проверка на минимальную конфигурацию. Если нет префикса и явно указанных сущностей,
        // выводим предупреждение. Это предупреждение нормально на этапе настройки.
        if (!config.entity_prefix && !config.warning_temp_entity && !config.max_pwm_fan_entity &&
            !config.save_settings_button && !config.reset_settings_button && !config.load_settings_button) {
            console.warn('Вы должны определить entity_prefix или явно указать сущности в конфигурации карточки.');
        }
        // Копируем конфигурацию, чтобы избежать прямых изменений
        this.config = { ...config };
    }

    updated(changedProperties) {
        if (changedProperties.has('hass') && this.hass) {
            this._updateEntities();
        }
    }

    _updateEntities() {
        const prefix = this.config.entity_prefix;
        const newEntities = {};

        const sensorKeys = [
            "temperatura_vykhlopa",
            "skorost_ventiliatora",
            "raskhod_topliva_gts",
            "rezhim_goreniia",
            "popytka_zapuska",
            "sostoianie",
            "ssid_wi_fi",
            "ip_adres_wi_fi",
            "tekushchee_potreblenie_topliva",
            "raschetnyi_raskhod_za_chas",
            "tekushchii_rezhim"
        ];
        sensorKeys.forEach(key => {
            newEntities[`sensor_${key}`] = this.hass.states[`sensor.${prefix}_${key}`];
        });

        const binarySensorKeys = [
            "gorenie_aktivno",
            "oshibka_webasto",
            "svecha_nakalivaniia",
            "prokachka_topliva",
            "logirovanie_vkliucheno",
            "wi_fi_podkliuchen"
        ];
        binarySensorKeys.forEach(key => {
            newEntities[`binary_sensor_${key}`] = this.hass.states[`binary_sensor.${prefix}_${key}`];
        });

        const numberKeys = [
            "razmer_nasosa",
            "tselevaia_temperatura_nagrevatelia",
            "minimalnaia_temperatura_nagrevatelia",
            "temperatura_peregreva",
            "temperatura_preduprezhdeniia", 
            "maks_shim_ventiliatora", 
            "iarkost_svechi_nakalivaniia",
            "vremia_rozzhiga_svechi",
            "vremia_zatukhaniia_svechi"
        ];
        numberKeys.forEach(key => {
            let entityId;
            // Приоритет явно указанным сущностям из конфигурации редактора
            if (key === 'temperatura_preduprezhdeniia' && this.config.warning_temp_entity) {
                entityId = this.config.warning_temp_entity;
            } else if (key === 'maks_shim_ventiliatora' && this.config.max_pwm_fan_entity) {
                entityId = this.config.max_pwm_fan_entity;
            } else {
                entityId = `number.${prefix}_${key}`;
            }
            newEntities[`number_${key}`] = this.hass.states[entityId];
        });

        const buttonKeys = [
            "vkliuchit_vykliuchit",
            "rezhim_vverkh",
            "rezhim_vniz",
            "prokachka_topliva",
            "sbrosit_oshibku",
            "sokhranit_nastroiki",
            "sbrosit_nastroiki",
            "zagruzit_nastroiki",
            "sbrosit_wi_fi",
            "perezagruzit_esp",
            "sbrosit_potreblenie_topliva",
            "vkliuchit_logirovanie",
            "vykliuchit_logirovanie"
        ];
        buttonKeys.forEach(key => {
            let entityId;
            // Приоритет явно указанным сущностям из конфигурации редактора
            if (key === 'sokhranit_nastroiki' && this.config.save_settings_button) {
                entityId = this.config.save_settings_button;
            } else if (key === 'sbrosit_nastroiki' && this.config.reset_settings_button) {
                entityId = this.config.reset_settings_button;
            } else if (key === 'zagruzit_nastroiki' && this.config.load_settings_button) {
                entityId = this.config.load_settings_button;
            } else {
                entityId = `button.${prefix}_${key}`;
            }
            newEntities[`button_${key}`] = this.hass.states[entityId];
        });

        this._entities = newEntities;
        this.requestUpdate(); // Запрашиваем обновление компонента
    }

    _callService(domain, service, entityId, value = null) {
        if (!this.hass) {
            console.error('Объект Hass недоступен.');
            return;
        }

        const serviceData = { entity_id: entityId };
        if (value !== null) {
            serviceData.value = value;
        }

        this.hass.callService(domain, service, serviceData)
            .then(() => {
                console.log(`Сервис ${domain}.${service} успешно вызван для ${entityId}`);
            })
            .catch(error => {
                console.error(`Ошибка вызова сервиса ${domain}.${service} для ${entityId}:`, error);
            });
    }

    _renderSection(title, content, subtitle = '') {
        return html`
            <div class="mb-4 bg-gray-700 rounded-lg shadow-md p-4 mx-1">
                <h2 class="text-lg font-semibold text-white mb-1">${title}</h2>
                ${subtitle ? html`<p class="text-xs text-gray-400 mb-2">${subtitle}</p>` : ''}
                <div>
                    ${content}
                </div>
            </div>
        `;
    }

    _renderSensor(key, name, unit = '') {
        const entity = this._entities[`sensor_${key}`];
        let state = entity ? entity.state : 'Неизвестно';
        const icon = entity ? entity.attributes.icon : 'mdi:gauge';

        if (state !== 'Неизвестно' && !isNaN(parseFloat(state))) {
            if (key === 'temperatura_vykhlopa') {
                state = parseFloat(state).toFixed(1);
            } else if (key === 'raskhod_topliva_gts' || key === 'tekushchee_potreblenie_topliva' || key === 'raschetnyi_raskhod_za_chas') {
                // Расход топлива и расход за час с двумя знаками после запятой
                state = parseFloat(state).toFixed(2);
            } else if (key === 'skorost_ventiliatora') {
                // Скорость вентилятора как целое число
                state = parseInt(parseFloat(state)).toString();
            }
        }

        return html`
            <div class="flex items-center p-2 bg-gray-800 rounded-md mb-2">
                <ha-icon .icon=${icon} class="text-blue-400 mr-2"></ha-icon>
                <span class="text-gray-300 text-sm">${name}:</span>
                <span class="text-white font-medium ml-auto text-sm">${state} ${unit}</span>
            </div>
        `;
    }

    _renderBinarySensor(key, name, displayAsYesNo = false) {
        const entity = this._entities[`binary_sensor_${key}`];
        const state = entity ? entity.state : 'Неизвестно';
        const icon = entity ? entity.attributes.icon : 'mdi:toggle-switch-off-outline';
        
        let stateText;
        let textColor;

        if (displayAsYesNo) {
            stateText = state === 'on' ? 'Да' : (state === 'off' ? 'Нет' : 'Неизвестно');
            textColor = state === 'on' ? 'text-green-400' : (state === 'off' ? 'text-red-400' : 'text-gray-400');
        } else if (key === 'svecha_nakalivaniia') {
            stateText = state === 'on' ? 'Включена' : (state === 'off' ? 'Выключена' : 'Неизвестно');
            textColor = state === 'on' ? 'text-green-400' : (state === 'off' ? 'text-red-400' : 'text-gray-400');
        } else {
            stateText = state === 'on' ? 'Активно' : (state === 'off' ? 'Неактивно' : 'Неизвестно');
            textColor = state === 'on' ? 'text-green-400' : (state === 'off' ? 'text-red-400' : 'text-gray-400');
        }

        return html`
            <div class="flex items-center p-2 bg-gray-800 rounded-md mb-2">
                <ha-icon .icon=${icon} class="text-blue-400 mr-2"></ha-icon>
                <span class="text-gray-300 text-sm">${name}:</span>
                <span class="font-medium ${textColor} ml-auto text-sm">${stateText}</span>
            </div>
        `;
    }

    _renderNumber(key, name, unit = '') {
        const entity = this._entities[`number_${key}`];
        const value = entity ? parseFloat(entity.state) : 0;
        const min = entity ? entity.attributes.min : 0;
        const max = entity ? entity.attributes.max : 100;
        const step = entity ? entity.attributes.step : 1;
        const icon = entity ? entity.attributes.icon : 'mdi:numeric';

        return html`
            <div class="flex flex-col p-2 bg-gray-800 rounded-md mb-2">
                <div class="flex items-center mb-1">
                    <ha-icon .icon=${icon} class="text-blue-400 mr-2"></ha-icon>
                    <span class="text-gray-300 text-sm">${name}:</span>
                    <span class="text-white font-medium ml-auto text-sm">${value !== undefined && !isNaN(value) ? `${value}${unit}` : 'Неизвестно'}</span>
                </div>
                <input
                    type="range"
                    min="${min}"
                    max="${max}"
                    step="${step}"
                    .value="${value}"
                    @change="${e => this._callService('number', 'set_value', entity.entity_id, parseFloat(e.target.value))}"
                    class="w-full h-1.5 bg-gray-600 rounded-lg appearance-none cursor-pointer range-sm"
                >
            </div>
        `;
    }

    _renderButton(key, name, icon, isRed = false, fullWidth = false, customClass = '', small = false) {
        const entity = this._entities[`button_${key}`];
        const entityId = entity ? entity.entity_id : null;
        const isDisabled = !entityId || !this.hass; 

        let buttonColorClass = "";
        if (isRed) {
            buttonColorClass = "red-button";
        } else if (customClass === 'dark-button') {
            buttonColorClass = "dark-button";
        } else {
            buttonColorClass = "blue-button";
        }
        
        return html`
            <button
                @click="${() => entityId && this._callService('button', 'press', entityId)}"
                ?disabled="${isDisabled}"
                class="custom-button ${buttonColorClass} ${fullWidth ? 'w-full' : ''} ${small ? 'small-button' : ''}"
                style="${!fullWidth ? 'flex: 1;' : ''}"
            >
                ${icon ? html`<ha-icon .icon=${icon} class="${small ? 'mr-1' : 'mr-2'}"></ha-icon>` : ''}
                <span class="${small ? 'text-xs' : ''}">${name}</span>
            </button>
        `;
    }

    render() {
        if (!this.hass || !this.config) {
            return html`
                <ha-card>
                    <div class="card-content text-center text-gray-400">
                        Загрузка...
                    </div>
                </ha-card>
            `;
        }

        const tabs = [
            { id: 'main', name: 'Управление' },
            { id: 'settings', name: 'Настройки' },
            { id: 'wifi', name: 'Wi-Fi' },
            { id: 'fuel', name: 'Топливо' },
        ];

        const messageEntity = this._entities['sensor_sostoianie'];
        const burnEntity = this._entities['binary_sensor_gorenie_aktivno'];
        const messageState = messageEntity ? messageEntity.state : 'Неизвестно';
        const burnState = burnEntity ? burnEntity.state : 'off';

        const statusIndicatorColor = burnState === 'on' ? 'bg-green-500' : 'bg-red-500';

        // Получаем цвет фона и прозрачность из конфигурации, с запасными значениями по умолчанию
        const customBackgroundColor = this.config.background_color;
        const customBackgroundOpacity = this.config.background_opacity;

        const defaultBackgroundColor = '#1f2937'; // Оригинальный цвет фона
        const defaultBackgroundOpacity = 1; // Оригинальная прозрачность

        const finalBackgroundColor = customBackgroundColor || defaultBackgroundColor;
        const finalBackgroundOpacity = customBackgroundOpacity !== undefined ? customBackgroundOpacity : defaultBackgroundOpacity;

        const cardStyles = styleMap({
            'background-color': finalBackgroundColor, // Применяем цвет фона напрямую
            'opacity': finalBackgroundOpacity,        // Применяем прозрачность напрямую
            '--ha-card-background': finalBackgroundColor, // Сохраняем переменную для использования в других элементах (например, вкладках)
        });

        return html`
            <ha-card class="text-white rounded-lg shadow-xl font-inter" style=${cardStyles}>
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
                    
                    :host {
                        display: block;
                        font-family: 'Inter', sans-serif;
                    }
                    ha-card {
                        /* Эти переменные будут установлены через inline style. */ 
                        --primary-text-color: #f9fafb;
                        --secondary-text-color: #d1d5db;
                        --mdc-icon-size: 20px;
                        border-radius: 0.75rem;
                        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                        /* background-color и opacity теперь устанавливаются через styleMap */
                    }
                    .card-content {
                        padding: 0 12px 12px;
                    }
                    input[type="range"]::-webkit-slider-thumb {
                        -webkit-appearance: none;
                        appearance: none;
                        width: 14px;
                        height: 14px;
                        border-radius: 50%;
                        background: #3b82f6;
                        cursor: pointer;
                        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                    }
                    input[type="range"]::-moz-range-thumb {
                        width: 14px;
                        height: 14px;
                        border-radius: 50%;
                        background: #3b82f6;
                        cursor: pointer;
                        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                    }
                    .tab-container {
                        display: flex;
                        justify-content: center;
                        border-bottom: 1px solid #374151;
                        margin-bottom: 12px;
                        padding: 0 8px;
                    }
                    .tab-button {
                        padding: 6px 12px;
                        font-size: 0.75rem;
                        font-weight: 600;
                        color: #d1d5db;
                        transition: all 0.2s ease-in-out;
                        background-color: #374151;
                        border-radius: 4px 4px 0 0;
                        margin: 0 2px;
                        border: none;
                        position: relative;
                        bottom: -1px;
                        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                        height: 28px;
                    }
                    .tab-button.active {
                        background-color: var(--ha-card-background); /* Используем цвет фона карточки */
                        color: #f9fafb;
                        box-shadow: 0 0 0 1px #3b82f6, 0 2px 4px rgba(0, 0, 0, 0.1);
                    }
                    .tab-button:hover:not(.active) {
                        background-color: #4b5563;
                        color: #e5e7eb;
                    }
                    .tab-content {
                        padding: 0 8px;
                    }
                    .status-indicator {
                        width: 10px;
                        height: 10px;
                        border-radius: 50%;
                        display: inline-block;
                        margin-left: 6px;
                    }
                    .custom-button {
                        padding: 0.5rem 1rem;
                        font-size: 0.875rem;
                        font-weight: 600;
                        border-radius: 0.375rem;
                        box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.06);
                        transition: all 0.2s ease-in-out;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        text-align: center;
                        color: white;
                        border: none;
                        height: 36px;
                    }
                    .small-button {
                        padding: 0.375rem 0.75rem;
                        font-size: 0.75rem;
                        height: 32px;
                    }
                    .custom-button:disabled {
                        opacity: 0.5;
                        cursor: not-allowed;
                    }
                    .custom-button.blue-button {
                        background-color: #3b82f6;
                        background-image: linear-gradient(to bottom, #3b82f6, #2563eb);
                        border: 1px solid #2563eb;
                    }
                    .custom-button.blue-button:hover:not(:disabled) {
                        background-color: #2563eb;
                        background-image: linear-gradient(to bottom, #2563eb, #1e40af);
                    }
                    .custom-button.dark-button {
                        background-color: #374151;
                        background-image: linear-gradient(to bottom, #374151, #1f2937);
                        border: 1px solid #1f2937;
                    }
                    .custom-button.dark-button:hover:not(:disabled) {
                        background-color: #1f2937;
                        background-image: linear-gradient(to bottom, #1f2937, #111827);
                    }
                    .custom-button.red-button {
                        background-color: #ef4444;
                        background-image: linear-gradient(to bottom, #ef4444, #dc2626);
                        border: 1px solid #dc2626;
                    }
                    .custom-button.red-button:hover:not(:disabled) {
                        background-color: #dc2626;
                        background-image: linear-gradient(to bottom, #dc2626, #b91c1c);
                    }
                    .button-row {
                        display: flex;
                        gap: 8px;
                        width: 100%;
                    }
                    .button-row > .custom-button {
                        flex: 1;
                    }
                    .compact-buttons {
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
                        gap: 8px;
                        width: 100%;
                    }
                    .compact-buttons > .custom-button {
                        margin: 0;
                    }
					.control-grid {
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 8px;
                        width: 100%;
                    }
                    
                    .wide-button {
                        grid-column: span 2;
                    }
                    
                    .mode-buttons {
                        display: flex;
                        gap: 8px;
                        margin-bottom: 8px;
                    }
                    
                    .mode-buttons > .custom-button {
                        flex: 1;
                    }
                </style>

                <div class="card-content">
                    <h1 class="text-xl font-bold text-white mb-4 text-center pt-3">Webasto</h1>

                    <div class="tab-container">
                        ${tabs.map(tab => html`
                            <button
                                class="tab-button ${this._activeTab === tab.id ? 'active' : ''}"
                                @click="${() => this._activeTab = tab.id}"
                            >
                                ${tab.name}
                            </button>
                        `)}
                    </div>

                    <div class="tab-content">
                        ${this._activeTab === 'main' ? html`
                            ${this._renderSection('Текущий статус', html`
                                <div class="grid grid-cols-1 gap-2">
                                    <div class="flex items-center p-2 bg-gray-800 rounded-md">
                                        <span class="text-gray-300 text-sm">Состояние:</span>
                                        <span class="text-white font-medium ml-auto text-sm">${messageState} <span class="status-indicator ${statusIndicatorColor}"></span></span>
                                    </div>
									${this._renderSensor('temperatura_vykhlopa', 'Температура выхлопа', '°C')}
									${this._renderSensor('skorost_ventiliatora', 'Скорость вентилятора', '%')}
									${this._renderSensor('raskhod_topliva_gts', 'Расход топлива', 'Гц')}
									${this._renderBinarySensor('svecha_nakalivaniia', 'Свеча', false)}
									${this._renderSensor('rezhim_goreniia', 'Режим горения')}
									${this._renderSensor('popytka_zapuska', 'Попытка запуска')}
									${this._renderBinarySensor('oshibka_webasto', 'Ошибки', true)}
									${this._renderSensor('tekushchii_rezhim', 'Текущий режим')}
									${this._renderBinarySensor('prokachka_topliva', 'Прокачка топлива', true)}
                                </div>
                            `)}

                            ${this._renderSection('Управление', html`
                                <div class="control-grid">
                                    <!-- Основная кнопка включения -->
                                    ${this._renderButton('vkliuchit_vykliuchit', 
                                        burnState === 'on' ? 'Выключить' : 'Включить', 
                                        burnState === 'on' ? 'mdi:power' : 'mdi:power-off', 
                                        false, true, '', false)}
                                    
                                    <!-- Кнопки режимов -->
                                    <div class="mode-buttons wide-button">
                                        ${this._renderButton('rezhim_vverkh', 'Понизить', 'mdi:chevron-down', false, false, 'dark-button')}
                                        ${this._renderButton('rezhim_vniz', 'Повысить', 'mdi:chevron-up', false, false, 'dark-button')}
                                    </div>
                                    
                                    <!-- Дополнительные функции -->
                                    ${this._renderButton('prokachka_topliva', 'Прокачка', 'mdi:fuel', false, false, 'dark-button')}
                                    ${this._renderButton('sbrosit_oshibku', 'Сброс ошибки', 'mdi:alert-circle-outline', true, false, '', false)}
                                </div>
                            `)}
                        ` : ''}

                        ${this._activeTab === 'settings' ? html`
                            ${this._renderSection('Настройки нагревателя', html`
                                <div class="grid grid-cols-1 gap-2">
                                    ${this._renderNumber('tselevaia_temperatura_nagrevatelia', 'Целевая температура', '°C')}
                                    ${this._renderNumber('minimalnaia_temperatura_nagrevatelia', 'Мин. температура', '°C')}
                                    ${this._renderNumber('temperatura_peregreva', 'Темп. перегрева', '°C')}
                                    ${this._renderNumber('temperatura_preduprezhdeniia', 'Темп. предупреждения', '°C')}
                                </div>
                            `)}
                            
                            ${this._renderSection('Настройки системы', html`
                                <div class="grid grid-cols-1 gap-2">
                                    ${this._renderNumber('razmer_nasosa', 'Размер насоса')}
                                    ${this._renderNumber('maks_shim_ventiliatora', 'Макс. ШИМ вентилятора')}
                                    ${this._renderNumber('iarkost_svechi_nakalivaniia', 'Яркость свечи')}
                                    ${this._renderNumber('vremia_rozzhiga_svechi', 'Время розжига', 'мс')}
                                    ${this._renderNumber('vremia_zatukhaniia_svechi', 'Время затухания', 'мс')}
                                </div>
                            `)}
                            
                            <div class="compact-buttons mt-4">
                                ${this._renderButton('sokhranit_nastroiki', 'Сохранить', 'mdi:content-save-outline', false, false, '', true)}
                                ${this._renderButton('sbrosit_nastroiki', 'Сбросить', 'mdi:restore', false, false, '', true)}
                                ${this._renderButton('zagruzit_nastroiki', 'Считать', 'mdi:download', false, false, '', true)}
                            </div>
                        ` : ''}

                        ${this._activeTab === 'wifi' ? html`
                            ${this._renderSection('Wi-Fi статус', html`
                                <div class="grid grid-cols-1 gap-2">
                                    ${this._renderBinarySensor('wi_fi_podkliuchen', 'Подключение')}
                                    ${this._renderSensor('ssid_wi_fi', 'SSID')}
                                    ${this._renderSensor('ip_adres_wi_fi', 'IP Адрес')}
                                </div>
                            `)}
                            
                            <div class="compact-buttons mt-4">
                                ${this._renderButton('sbrosit_wi_fi', 'Сбросить Wi-Fi', 'mdi:wifi-off', false, false, '', true)}
                                ${this._renderButton('perezagruzit_esp', 'Перезагрузить', 'mdi:restart', false, false, '', true)}
                            </div>
                        ` : ''}

                        ${this._activeTab === 'fuel' ? html`
                            ${this._renderSection('Расход топлива', html`
                                <div class="grid grid-cols-1 gap-2">
                                    ${this._renderSensor('tekushchee_potreblenie_topliva', 'Текущий расход', 'л')}
                                    ${this._renderSensor('raschetnyi_raskhod_za_chas', 'Расход за час', 'л/ч')}
                                </div>
                            `)}
                            
                            <div class="mt-4">
                                ${this._renderButton('sbrosit_potreblenie_topliva', 'Сбросить расход', 'mdi:fuel-off', false, true, '', true)}
                            </div>
                        ` : ''}
                    </div>
                </div>
            </ha-card>
        `;
    }

    getCardSize() {
        return 8;
    }

    // Метод getEditorElement() удален.

}

// Определяем пользовательский элемент карточки
customElements.define('webastoheater-card', WebastoHeaterCard);

// Добавляем метаданные для Home Assistant.
// configurable теперь установлен в false, так как визуальный редактор удален.
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'webastoheater-card',
  name: 'Карточка управления Webasto',
  description: 'Карточка для управления Webasto с расширенными настройками',
  preview: true, // Предварительный просмотр все еще доступен
  configurable: false, // Визуальный редактор не поддерживается
});