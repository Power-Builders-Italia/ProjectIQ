/*
 * ATTENTION: The "eval" devtool has been used (maybe by default in mode: "development").
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
var pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad;
/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ({

/***/ "./ProgressField/index.ts"
/*!********************************!*\
  !*** ./ProgressField/index.ts ***!
  \********************************/
(__unused_webpack_module, __webpack_exports__, __webpack_require__) {

eval("{__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   ProgressField: () => (/* binding */ ProgressField)\n/* harmony export */ });\n/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react */ \"react\");\n/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(react__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var _fluentui_react_components__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @fluentui/react-components */ \"@fluentui/react-components\");\n/* harmony import */ var _fluentui_react_components__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_fluentui_react_components__WEBPACK_IMPORTED_MODULE_1__);\n/* harmony import */ var _shared_ProgressCell__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ../shared/ProgressCell */ \"./shared/ProgressCell.tsx\");\n/* harmony import */ var _shared_progress__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ../shared/progress */ \"./shared/progress.ts\");\n\n\n\n\nclass ProgressField {\n  init() {\n    // read-only: nothing to set up\n  }\n  updateView(context) {\n    var _a, _b, _c;\n    var theme = (_b = (_a = context.fluentDesignLanguage) === null || _a === void 0 ? void 0 : _a.tokenTheme) !== null && _b !== void 0 ? _b : _fluentui_react_components__WEBPACK_IMPORTED_MODULE_1__.webLightTheme;\n    var pct = (_c = (0,_shared_progress__WEBPACK_IMPORTED_MODULE_3__.progressPercent)(context.parameters.value.raw)) !== null && _c !== void 0 ? _c : 0;\n    return /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0__.createElement(_fluentui_react_components__WEBPACK_IMPORTED_MODULE_1__.FluentProvider, {\n      theme,\n      style: {\n        background: \"transparent\"\n      }\n    }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0__.createElement(_shared_ProgressCell__WEBPACK_IMPORTED_MODULE_2__.ProgressCell, {\n      pct\n    }));\n  }\n  getOutputs() {\n    return {};\n  }\n  destroy() {\n    // nothing to release\n  }\n}\n\n//# sourceURL=webpack://pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad/./ProgressField/index.ts?\n}");

/***/ },

/***/ "./shared/ProgressCell.tsx"
/*!*********************************!*\
  !*** ./shared/ProgressCell.tsx ***!
  \*********************************/
(__unused_webpack_module, __webpack_exports__, __webpack_require__) {

eval("{__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   ProgressCell: () => (/* binding */ ProgressCell)\n/* harmony export */ });\n/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react */ \"react\");\n/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(react__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var _fluentui_react_components__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @fluentui/react-components */ \"@fluentui/react-components\");\n/* harmony import */ var _fluentui_react_components__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_fluentui_react_components__WEBPACK_IMPORTED_MODULE_1__);\n/* harmony import */ var _progress__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ./progress */ \"./shared/progress.ts\");\n\n\n\n// Brand green bar on a light grey track, percentage on the right (approved mockup A, single colour)\nvar useStyles = (0,_fluentui_react_components__WEBPACK_IMPORTED_MODULE_1__.makeStyles)({\n  cell: {\n    display: \"flex\",\n    alignItems: \"center\",\n    columnGap: \"10px\",\n    width: \"100%\",\n    minWidth: \"120px\",\n    boxSizing: \"border-box\"\n  },\n  track: {\n    flexGrow: 1,\n    minWidth: \"40px\",\n    height: \"8px\",\n    backgroundColor: \"#e8e6e5\",\n    borderRadius: \"4px\"\n  },\n  bar: {\n    backgroundColor: \"#0c723d\",\n    borderRadius: \"4px\"\n  },\n  label: {\n    minWidth: \"40px\",\n    textAlign: \"right\",\n    fontVariantNumeric: \"tabular-nums\"\n  }\n});\nfunction ProgressCell(_ref) {\n  var pct = _ref.pct,\n    label = _ref.label;\n  var s = useStyles();\n  var text = (0,_progress__WEBPACK_IMPORTED_MODULE_2__.progressLabel)(pct);\n  return /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0__.createElement(\"div\", {\n    className: s.cell,\n    title: text\n  }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0__.createElement(_fluentui_react_components__WEBPACK_IMPORTED_MODULE_1__.ProgressBar, {\n    className: s.track,\n    bar: {\n      className: s.bar\n    },\n    value: pct / 100,\n    thickness: \"large\",\n    shape: \"rounded\",\n    \"aria-label\": text\n  }), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0__.createElement(\"span\", {\n    className: s.label\n  }, label !== null && label !== void 0 ? label : text));\n}\n\n//# sourceURL=webpack://pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad/./shared/ProgressCell.tsx?\n}");

/***/ },

/***/ "./shared/progress.ts"
/*!****************************!*\
  !*** ./shared/progress.ts ***!
  \****************************/
(__unused_webpack_module, __webpack_exports__, __webpack_require__) {

eval("{__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   isProgressColumn: () => (/* binding */ isProgressColumn),\n/* harmony export */   progressLabel: () => (/* binding */ progressLabel),\n/* harmony export */   progressPercent: () => (/* binding */ progressPercent)\n/* harmony export */ });\n/** Progress columns rendered as a bar in the Power Apps grid (Project and WBS Node: op365_progresspct). */\nvar isProgressColumn = name => !!name && /progresspct/i.test(name);\n/** Bar fill in percent, clamped to 0-100; null when the cell is empty. */\nfunction progressPercent(value, formatted) {\n  if (value === null || value === undefined || value === \"\") {\n    if (!formatted) return null;\n    value = formatted;\n  }\n  // the grid may hand over the formatted text (\"43,62\" with a comma decimal separator)\n  var n = typeof value === \"number\" ? value : Number(String(value).replace(/[\\s%]/g, \"\").replace(\",\", \".\"));\n  if (!isFinite(n)) return null;\n  return Math.min(100, Math.max(0, n));\n}\n/** Label shown next to the bar: whole percent. */\nvar progressLabel = pct => \"\".concat(Math.round(pct), \"%\");\n\n//# sourceURL=webpack://pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad/./shared/progress.ts?\n}");

/***/ },

/***/ "@fluentui/react-components"
/*!************************************!*\
  !*** external "FluentUIReactv940" ***!
  \************************************/
(module) {

module.exports = FluentUIReactv940;

/***/ },

/***/ "react"
/*!***************************!*\
  !*** external "Reactv16" ***!
  \***************************/
(module) {

module.exports = Reactv16;

/***/ }

/******/ 	});
/************************************************************************/
/******/ 	// The module cache
/******/ 	const __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		const cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		const module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		if (!(moduleId in __webpack_modules__)) {
/******/ 			delete __webpack_module_cache__[moduleId];
/******/ 			const e = new Error("Cannot find module '" + moduleId + "'");
/******/ 			e.code = 'MODULE_NOT_FOUND';
/******/ 			throw e;
/******/ 		}
/******/ 		__webpack_modules__[moduleId](module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/compat get default export */
/******/ 	// getDefaultExport function for compatibility with non-harmony modules
/******/ 	__webpack_require__.n = (module) => {
/******/ 		const getter = module && module.__esModule ?
/******/ 			() => (module['default']) :
/******/ 			() => (module);
/******/ 		__webpack_require__.d(getter, { a: getter });
/******/ 		return getter;
/******/ 	};
/******/ 	
/******/ 	/* webpack/runtime/define property getters */
/******/ 	// define getter/value functions for harmony exports
/******/ 	__webpack_require__.d = (exports, definition) => {
/******/ 		for(var key in definition) {
/******/ 			if(__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
/******/ 				Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
/******/ 			}
/******/ 		}
/******/ 	};
/******/ 	
/******/ 	/* webpack/runtime/hasOwnProperty shorthand */
/******/ 	__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop));
/******/ 	
/******/ 	/* webpack/runtime/make namespace object */
/******/ 	// define __esModule on exports
/******/ 	__webpack_require__.r = (exports) => {
/******/ 		Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 		Object.defineProperty(exports, '__esModule', { value: true });
/******/ 	};
/******/ 	
/************************************************************************/
/******/ 	
/******/ 	// startup
/******/ 	// Load entry module and return exports
/******/ 	// This entry module can't be inlined because the eval devtool is used.
/******/ 	let __webpack_exports__ = __webpack_require__("./ProgressField/index.ts");
/******/ 	pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad = __webpack_exports__;
/******/ 	
/******/ })()
;
if (window.ComponentFramework && window.ComponentFramework.registerControl) {
	ComponentFramework.registerControl('OP365.ProgressField', pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad.ProgressField);
} else {
	var OP365 = OP365 || {};
	OP365.ProgressField = pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad.ProgressField;
	pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad = undefined;
}