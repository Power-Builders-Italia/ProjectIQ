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

/***/ "./ProgressBar/customizers/CellRendererOverrides.tsx"
/*!***********************************************************!*\
  !*** ./ProgressBar/customizers/CellRendererOverrides.tsx ***!
  \***********************************************************/
(__unused_webpack_module, __webpack_exports__, __webpack_require__) {

eval("{__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   cellRendererOverrides: () => (/* binding */ cellRendererOverrides)\n/* harmony export */ });\n/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react */ \"react\");\n/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(react__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var _fluentui_react_components__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! @fluentui/react-components */ \"@fluentui/react-components\");\n/* harmony import */ var _fluentui_react_components__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(_fluentui_react_components__WEBPACK_IMPORTED_MODULE_1__);\n/* harmony import */ var _shared_progress__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ../../shared/progress */ \"./shared/progress.ts\");\n\n\n\n// Brand green bar on a light grey track (mockup A, single colour)\nvar useStyles = (0,_fluentui_react_components__WEBPACK_IMPORTED_MODULE_1__.makeStyles)({\n  cell: {\n    display: \"flex\",\n    alignItems: \"center\",\n    columnGap: \"10px\",\n    width: \"100%\",\n    height: \"100%\",\n    boxSizing: \"border-box\"\n  },\n  track: {\n    flexGrow: 1,\n    minWidth: \"40px\",\n    height: \"8px\",\n    backgroundColor: \"#e8e6e5\",\n    borderRadius: \"4px\"\n  },\n  bar: {\n    backgroundColor: \"#0c723d\",\n    borderRadius: \"4px\"\n  },\n  label: {\n    minWidth: \"40px\",\n    textAlign: \"right\",\n    fontVariantNumeric: \"tabular-nums\"\n  }\n});\nvar ProgressCell = _ref => {\n  var pct = _ref.pct;\n  var s = useStyles();\n  var label = (0,_shared_progress__WEBPACK_IMPORTED_MODULE_2__.progressLabel)(pct);\n  return /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0__.createElement(\"div\", {\n    className: s.cell,\n    title: label\n  }, /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0__.createElement(_fluentui_react_components__WEBPACK_IMPORTED_MODULE_1__.ProgressBar, {\n    className: s.track,\n    bar: {\n      className: s.bar\n    },\n    value: pct / 100,\n    thickness: \"large\",\n    shape: \"rounded\",\n    \"aria-label\": label\n  }), /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0__.createElement(\"span\", {\n    className: s.label\n  }, label));\n};\nvar renderProgress = (props, params) => {\n  var _a;\n  if (!(0,_shared_progress__WEBPACK_IMPORTED_MODULE_2__.isProgressColumn)((_a = params.colDefs[params.columnIndex]) === null || _a === void 0 ? void 0 : _a.name)) return undefined; // default renderer\n  var pct = (0,_shared_progress__WEBPACK_IMPORTED_MODULE_2__.progressPercent)(props.value);\n  return pct === null ? undefined : /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0__.createElement(ProgressCell, {\n    pct: pct\n  });\n};\nvar cellRendererOverrides = {\n  Decimal: renderProgress,\n  FloatingPoint: renderProgress\n};\n\n//# sourceURL=webpack://pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad/./ProgressBar/customizers/CellRendererOverrides.tsx?\n}");

/***/ },

/***/ "./ProgressBar/index.ts"
/*!******************************!*\
  !*** ./ProgressBar/index.ts ***!
  \******************************/
(__unused_webpack_module, __webpack_exports__, __webpack_require__) {

eval("{__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   ProgressBar: () => (/* binding */ ProgressBar)\n/* harmony export */ });\n/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react */ \"react\");\n/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(react__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var _customizers_CellRendererOverrides__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! ./customizers/CellRendererOverrides */ \"./ProgressBar/customizers/CellRendererOverrides.tsx\");\n\n\nclass ProgressBar {\n  init(context) {\n    // The Power Apps grid passes an event name: answer it with the cell renderers\n    var eventName = context.parameters.EventName.raw;\n    if (eventName) {\n      var customizer = {\n        cellRendererOverrides: _customizers_CellRendererOverrides__WEBPACK_IMPORTED_MODULE_1__.cellRendererOverrides\n      };\n      // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access\n      context.factory.fireEvent(eventName, customizer);\n    }\n  }\n  updateView() {\n    return /*#__PURE__*/react__WEBPACK_IMPORTED_MODULE_0__.createElement(react__WEBPACK_IMPORTED_MODULE_0__.Fragment);\n  }\n  getOutputs() {\n    return {};\n  }\n  destroy() {\n    // nothing to release\n  }\n}\n\n//# sourceURL=webpack://pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad/./ProgressBar/index.ts?\n}");

/***/ },

/***/ "./shared/progress.ts"
/*!****************************!*\
  !*** ./shared/progress.ts ***!
  \****************************/
(__unused_webpack_module, __webpack_exports__, __webpack_require__) {

eval("{__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   isProgressColumn: () => (/* binding */ isProgressColumn),\n/* harmony export */   progressLabel: () => (/* binding */ progressLabel),\n/* harmony export */   progressPercent: () => (/* binding */ progressPercent)\n/* harmony export */ });\n/** Progress columns rendered as a bar in the Power Apps grid (Project and WBS Node: op365_progresspct). */\nvar isProgressColumn = name => !!name && /progresspct$/i.test(name);\n/** Bar fill in percent, clamped to 0-100; null when the cell is empty. */\nfunction progressPercent(value) {\n  if (value === null || value === undefined || value === \"\") return null;\n  var n = typeof value === \"number\" ? value : Number(value);\n  if (!isFinite(n)) return null;\n  return Math.min(100, Math.max(0, n));\n}\n/** Label shown next to the bar: whole percent. */\nvar progressLabel = pct => \"\".concat(Math.round(pct), \"%\");\n\n//# sourceURL=webpack://pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad/./shared/progress.ts?\n}");

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
/******/ 	let __webpack_exports__ = __webpack_require__("./ProgressBar/index.ts");
/******/ 	pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad = __webpack_exports__;
/******/ 	
/******/ })()
;
if (window.ComponentFramework && window.ComponentFramework.registerControl) {
	ComponentFramework.registerControl('OP365.ProgressBar', pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad.ProgressBar);
} else {
	var OP365 = OP365 || {};
	OP365.ProgressBar = pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad.ProgressBar;
	pcf_tools_652ac3f36e1e4bca82eb3c1dc44e6fad = undefined;
}