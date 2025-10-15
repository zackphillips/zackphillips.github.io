# ESP Engine Reader Makefile
# Provides convenient targets for building, uploading, and linting

# Variables
UV_CMD := uv
PIO_CMD := $(UV_CMD) run pio
PROJECT_DIR := $(shell pwd)
SRC_DIR := src
CLANG_TIDY_CONFIG := .clang-tidy

# Default target
.DEFAULT_GOAL := help

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Help target
.PHONY: help
help: ## Show this help message
	@echo "ESP Engine Reader - Available Make Targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

# Check if uv is installed
.PHONY: check-uv
check-uv:
	@which $(UV_CMD) > /dev/null 2>&1 || { \
		echo "$(RED)Error: uv is not installed$(NC)"; \
		echo "$(YELLOW)Please install uv from: https://docs.astral.sh/uv/getting-started/installation/$(NC)"; \
		echo "$(YELLOW)Or run: curl -LsSf https://astral.sh/uv/install.sh | sh$(NC)"; \
		exit 1; \
	}

# Install uv (for Unix-like systems)
.PHONY: install-uv
install-uv: ## Install uv package manager
	@echo "$(YELLOW)Installing uv...$(NC)"
	@if command -v curl >/dev/null 2>&1; then \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	elif command -v wget >/dev/null 2>&1; then \
		wget -qO- https://astral.sh/uv/install.sh | sh; \
	elif command -v powershell >/dev/null 2>&1; then \
		powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"; \
	else \
		echo "$(RED)Error: Cannot install uv automatically. Please install manually.$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)uv installed successfully!$(NC)"

# Sync dependencies
.PHONY: sync
sync: check-uv ## Sync project dependencies with uv
	@echo "$(YELLOW)Syncing dependencies...$(NC)"
	@$(UV_CMD) sync
	@echo "$(GREEN)Dependencies synced successfully!$(NC)"

# Build the project
.PHONY: build
build: check-uv sync ## Build the ESP32 project
	@echo "$(YELLOW)Building project...$(NC)"
	@$(PIO_CMD) run
	@echo "$(GREEN)Build completed successfully!$(NC)"

# Upload to ESP32
.PHONY: upload
upload: check-uv sync ## Upload firmware to ESP32 device
	@echo "$(YELLOW)Uploading to ESP32...$(NC)"
	@$(PIO_CMD) run --target upload
	@echo "$(GREEN)Upload completed successfully!$(NC)"

# Build and upload in one step
.PHONY: flash
flash: check-uv sync ## Build and upload firmware to ESP32 device
	@echo "$(YELLOW)Building and uploading to ESP32...$(NC)"
	@$(PIO_CMD) run --target upload
	@echo "$(GREEN)Flash completed successfully!$(NC)"

# Monitor serial output
.PHONY: monitor
monitor: check-uv ## Monitor serial output from ESP32
	@echo "$(YELLOW)Starting serial monitor...$(NC)"
	@$(PIO_CMD) device monitor

# Clean build files
.PHONY: clean
clean: check-uv ## Clean build artifacts
	@echo "$(YELLOW)Cleaning build files...$(NC)"
	@$(PIO_CMD) run --target clean
	@if [ -d ".pio" ]; then rm -rf .pio; fi
	@echo "$(GREEN)Clean completed!$(NC)"

# Deep clean including cached packages
.PHONY: clean-all
clean-all: clean ## Deep clean including PlatformIO cache
	@echo "$(YELLOW)Performing deep clean...$(NC)"
	@$(PIO_CMD) system prune --force || true
	@$(UV_CMD) cache clean || true
	@echo "$(GREEN)Deep clean completed!$(NC)"

# Lint C++ code using clang-tidy
.PHONY: lint
lint: check-uv sync ## Lint C++ code using clang-tidy
	@echo "$(YELLOW)Linting C++ code...$(NC)"
	@if [ ! -f "$(CLANG_TIDY_CONFIG)" ]; then \
		echo "$(YELLOW)Creating .clang-tidy configuration...$(NC)"; \
		$(MAKE) create-clang-tidy-config; \
	fi
	@$(PIO_CMD) check --tool clangtidy --verbose
	@echo "$(GREEN)Linting completed!$(NC)"

# Format C++ code
.PHONY: format
format: check-uv ## Format C++ code using clang-format
	@echo "$(YELLOW)Formatting C++ code...$(NC)"
	@find $(SRC_DIR) -name "*.cpp" -o -name "*.hpp" -o -name "*.c" -o -name "*.h" | xargs clang-format -i --style=file || \
		echo "$(RED)clang-format not found. Please install it to use this target.$(NC)"
	@echo "$(GREEN)Formatting completed!$(NC)"

# Create clang-tidy configuration if it doesn't exist
.PHONY: create-clang-tidy-config
create-clang-tidy-config: ## Create default .clang-tidy configuration
	@echo "$(YELLOW)Creating .clang-tidy configuration...$(NC)"
	@cat > $(CLANG_TIDY_CONFIG) << 'EOF'
---
Checks: >
  -*,
  bugprone-*,
  clang-analyzer-*,
  cppcoreguidelines-*,
  modernize-*,
  performance-*,
  portability-*,
  readability-*,
  -modernize-use-trailing-return-type,
  -cppcoreguidelines-avoid-magic-numbers,
  -readability-magic-numbers,
  -cppcoreguidelines-pro-bounds-pointer-arithmetic,
  -cppcoreguidelines-pro-bounds-array-to-pointer-decay

WarningsAsErrors: ''
HeaderFilterRegex: '.*'
AnalyzeTemporaryDtors: false
FormatStyle: file
CheckOptions:
  - key: readability-identifier-naming.ClassCase
    value: CamelCase
  - key: readability-identifier-naming.FunctionCase
    value: camelCase
  - key: readability-identifier-naming.VariableCase
    value: camelBack
  - key: readability-identifier-naming.ConstantCase
    value: UPPER_CASE
EOF
	@echo "$(GREEN).clang-tidy configuration created!$(NC)"

# List available serial ports
.PHONY: ports
ports: check-uv ## List available serial ports
	@echo "$(YELLOW)Available serial ports:$(NC)"
	@$(PIO_CMD) device list

# Get project info
.PHONY: info
info: check-uv ## Show project information
	@echo "$(YELLOW)Project Information:$(NC)"
	@echo "Project Directory: $(PROJECT_DIR)"
	@echo "Source Directory: $(SRC_DIR)"
	@$(PIO_CMD) project config
	@echo ""
	@$(UV_CMD) tree || $(UV_CMD) pip list

# Install project in development mode
.PHONY: dev-install
dev-install: check-uv ## Install project dependencies for development
	@echo "$(YELLOW)Installing development dependencies...$(NC)"
	@$(UV_CMD) sync --dev
	@echo "$(GREEN)Development dependencies installed!$(NC)"

# Run tests (if any)
.PHONY: test
test: check-uv sync ## Run tests
	@echo "$(YELLOW)Running tests...$(NC)"
	@$(PIO_CMD) test
	@echo "$(GREEN)Tests completed!$(NC)"

# Update dependencies
.PHONY: update
update: check-uv ## Update project dependencies
	@echo "$(YELLOW)Updating dependencies...$(NC)"
	@$(UV_CMD) lock --upgrade
	@$(UV_CMD) sync
	@echo "$(GREEN)Dependencies updated!$(NC)"

# Create clang-format configuration
.PHONY: create-clang-format-config
create-clang-format-config: ## Create default .clang-format configuration
	@echo "$(YELLOW)Creating .clang-format configuration...$(NC)"
	@cat > .clang-format << 'EOF'
---
Language: Cpp
BasedOnStyle: Google
AccessModifierOffset: -2
AlignAfterOpenBracket: Align
AlignConsecutiveAssignments: false
AlignConsecutiveDeclarations: false
AlignOperands: true
AlignTrailingComments: true
AllowAllParametersOfDeclarationOnNextLine: true
AllowShortBlocksOnASingleLine: false
AllowShortCaseLabelsOnASingleLine: false
AllowShortFunctionsOnASingleLine: All
AllowShortIfStatementsOnASingleLine: true
AllowShortLoopsOnASingleLine: true
AlwaysBreakAfterDefinitionReturnType: None
AlwaysBreakAfterReturnType: None
AlwaysBreakBeforeMultilineStrings: true
AlwaysBreakTemplateDeclarations: true
BinPackArguments: true
BinPackParameters: true
BraceWrapping:
  AfterClass: false
  AfterControlStatement: false
  AfterEnum: false
  AfterFunction: false
  AfterNamespace: false
  AfterObjCDeclaration: false
  AfterStruct: false
  AfterUnion: false
  BeforeCatch: false
  BeforeElse: false
  IndentBraces: false
BreakBeforeBinaryOperators: None
BreakBeforeBraces: Attach
BreakBeforeTernaryOperators: true
BreakConstructorInitializersBeforeComma: false
ColumnLimit: 100
CommentPragmas: '^ IWYU pragma:'
ConstructorInitializerAllOnOneLineOrOnePerLine: true
ConstructorInitializerIndentWidth: 4
ContinuationIndentWidth: 4
Cpp11BracedListStyle: true
DerivePointerAlignment: true
DisableFormat: false
ExperimentalAutoDetectBinPacking: false
ForEachMacros: [ foreach, Q_FOREACH, BOOST_FOREACH ]
IncludeCategories:
  - Regex: '^<.*\.h>'
    Priority: 1
  - Regex: '^<.*'
    Priority: 2
  - Regex: '.*'
    Priority: 3
IndentCaseLabels: true
IndentWidth: 2
IndentWrappedFunctionNames: false
KeepEmptyLinesAtTheStartOfBlocks: false
MacroBlockBegin: ''
MacroBlockEnd: ''
MaxEmptyLinesToKeep: 1
NamespaceIndentation: None
ObjCBlockIndentWidth: 2
ObjCSpaceAfterProperty: false
ObjCSpaceBeforeProtocolList: false
PenaltyBreakBeforeFirstCallParameter: 1
PenaltyBreakComment: 300
PenaltyBreakFirstLessLess: 120
PenaltyBreakString: 1000
PenaltyExcessCharacter: 1000000
PenaltyReturnTypeOnItsOwnLine: 200
PointerAlignment: Left
ReflowComments: true
SortIncludes: true
SpaceAfterCStyleCast: false
SpaceBeforeAssignmentOperators: true
SpaceBeforeParens: ControlStatements
SpaceInEmptyParentheses: false
SpacesBeforeTrailingComments: 2
SpacesInAngles: false
SpacesInContainerLiterals: true
SpacesInCStyleCastParentheses: false
SpacesInParentheses: false
SpacesInSquareBrackets: false
Standard: Auto
TabWidth: 8
UseTab: Never
EOF
	@echo "$(GREEN).clang-format configuration created!$(NC)"

# Setup development environment
.PHONY: setup
setup: check-uv sync create-clang-tidy-config create-clang-format-config ## Setup complete development environment
	@echo "$(GREEN)Development environment setup completed!$(NC)"
	@echo "$(YELLOW)Available targets:$(NC)"
	@$(MAKE) help