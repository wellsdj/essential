/* Copyright 2013-2019 Matt Tytel
 *
 * vital is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * vital is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with vital.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "sample_section.h"

#include "load_save.h"
#include "skin.h"
#include "fonts.h"
#include "paths.h"
#include "sample_viewer.h"
#include "synth_button.h"
#include "synth_gui_interface.h"
#include "synth_slider.h"
#include "synth_strings.h"
#include "text_look_and_feel.h"

SampleSection::SampleSection(String name) : SynthSection(std::move(name)), sample_(nullptr) {
  transpose_quantize_button_ = std::make_unique<TransposeQuantizeButton>();
  addOpenGlComponent(transpose_quantize_button_.get());
  transpose_quantize_button_->addQuantizeListener(this);

  transpose_ = std::make_unique<SynthSlider>("sample_transpose");
  addSlider(transpose_.get());
  transpose_->setLookAndFeel(TextLookAndFeel::instance());
  transpose_->setSliderStyle(Slider::RotaryHorizontalVerticalDrag);
  transpose_->setSensitivity(kTransposeMouseSensitivity);
  transpose_->setTextEntrySizePercent(1.0f, 0.7f);
  transpose_->setShiftIndexAmount(vital::kNotesPerOctave);
  transpose_->overrideValue(Skin::kTextComponentOffset, 0.0f);
  transpose_->setModulationBarRight(false);

  tune_ = std::make_unique<SynthSlider>("sample_tune");
  addSlider(tune_.get());
  tune_->setLookAndFeel(TextLookAndFeel::instance());
  tune_->setSliderStyle(Slider::RotaryHorizontalVerticalDrag);
  tune_->setMaxDisplayCharacters(3);
  tune_->setMaxDecimalPlaces(0);
  tune_->setTextEntrySizePercent(1.0f, 0.7f);
  tune_->overrideValue(Skin::kTextComponentOffset, 0.0f);

  level_ = std::make_unique<SynthSlider>("sample_level");
  addSlider(level_.get());
  level_->setSliderStyle(Slider::RotaryHorizontalVerticalDrag);

  pan_ = std::make_unique<SynthSlider>("sample_pan");
  addSlider(pan_.get());
  pan_->setBipolar();
  pan_->setSliderStyle(Slider::RotaryHorizontalVerticalDrag);

  sample_viewer_ = std::make_unique<SampleViewer>();
  addOpenGlComponent(sample_viewer_.get());
  addAndMakeVisible(sample_viewer_.get());
  sample_viewer_->addListener(this);

  preset_selector_ = std::make_unique<PresetSelector>();
  addSubSection(preset_selector_.get());
  preset_selector_->addListener(this);
  setPresetSelector(preset_selector_.get());

  destination_selector_ = std::make_unique<ShapeButton>("Destination", Colour(0xff666666),
                                                        Colour(0xffaaaaaa), Colour(0xff888888));

  current_destination_ = 0;
  destination_control_name_ = "sample_destination";
  destination_text_ = std::make_unique<PlainTextComponent>("Destination Text", "---");
  addOpenGlComponent(destination_text_.get());

  addAndMakeVisible(destination_selector_.get());
  destination_selector_->addListener(this);
  destination_selector_->setTriggeredOnMouseDown(true);
  destination_selector_->setShape(Path(), true, true, true);

  prev_destination_ = std::make_unique<OpenGlShapeButton>("Prev Destination");
  addAndMakeVisible(prev_destination_.get());
  addOpenGlComponent(prev_destination_->getGlComponent());
  prev_destination_->addListener(this);
  prev_destination_->setShape(Paths::prev());

  next_destination_ = std::make_unique<OpenGlShapeButton>("Next Destination");
  addAndMakeVisible(next_destination_.get());
  addOpenGlComponent(next_destination_->getGlComponent());
  next_destination_->addListener(this);
  next_destination_->setShape(Paths::next());

  keytrack_ = std::make_unique<OpenGlShapeButton>("sample_keytrack");
  keytrack_->useOnColors(true);
  keytrack_->setClickingTogglesState(true);
  addButton(keytrack_.get());
  keytrack_->addListener(this);
  keytrack_->setShape(Paths::keyboard());

  random_phase_ = std::make_unique<OpenGlShapeButton>("sample_random_phase");
  random_phase_->useOnColors(true);
  random_phase_->setClickingTogglesState(true);
  addButton(random_phase_.get());
  random_phase_->addListener(this);
  random_phase_->addListener(this);
  random_phase_->setShape(Paths::shuffle());

  loop_ = std::make_unique<OpenGlShapeButton>("sample_loop");
  loop_->useOnColors(true);
  loop_->setClickingTogglesState(true);
  addButton(loop_.get());
  loop_->addListener(this);
  loop_->setShape(Paths::loop());

  bounce_ = std::make_unique<OpenGlShapeButton>("sample_bounce");
  bounce_->useOnColors(true);
  bounce_->setClickingTogglesState(true);
  addButton(bounce_.get());
  bounce_->addListener(this);
  bounce_->setShape(Paths::bounce());

  on_ = std::make_unique<SynthButton>("sample_on");
  addButton(on_.get());
  setActivator(on_.get());
  setSkinOverride(Skin::kSample);
}

SampleSection::~SampleSection() = default;

void SampleSection::parentHierarchyChanged() {
  SynthGuiInterface* parent = findParentComponentOfClass<SynthGuiInterface>();

  if (sample_ == nullptr && parent) {
    sample_ = parent->getSynth()->getSample();
    sample_viewer_->setSample(sample_);
    sample_viewer_->repaintAudio();
    reset();
  }
}

void SampleSection::paintBackground(Graphics& g) {
  if (getWidth() == 0)
    return;

  paintContainer(g);
  paintHeadingText(g);

  paintKnobShadows(g);

  setLabelFont(g);
  drawLabelForComponent(g, TRANS("PAN"), pan_.get());
  drawLabelForComponent(g, TRANS("LEVEL"), level_.get());

  int widget_margin = findValue(Skin::kWidgetMargin);
  int section_width = getWidth() * 0.19f;
  int component_width = section_width - 2 * widget_margin;

  int pitch_x = findValue(Skin::kTitleWidth);
  int section2_x = getWidth() - 2 * section_width + widget_margin;
  int label_height = findValue(Skin::kLabelBackgroundHeight);
  int top_row_y = widget_margin;
  int text_component_height = destination_selector_->getY() - top_row_y - widget_margin;
  paintJointControl(g, pitch_x + widget_margin, top_row_y, component_width, text_component_height, "");

  g.drawText("PITCH", pitch_x + widget_margin, widget_margin, component_width, label_height,
             Justification::centred, false);

  float label_rounding = findValue(Skin::kLabelBackgroundRounding);
  g.setColour(findColour(Skin::kTextComponentBackground, true));

  g.fillRoundedRectangle(destination_selector_->getBounds().toFloat(), label_rounding);

  int buttons_x = section2_x + section_width;
  g.fillRoundedRectangle(buttons_x, widget_margin, component_width, getHeight() - 2 * widget_margin, label_rounding);

  g.setColour(findColour(Skin::kWidgetBackground, true));
  g.fillRoundedRectangle(sample_viewer_->getX(), widget_margin,
                         sample_viewer_->getWidth(), getHeight() - 2 * widget_margin,
                         findValue(Skin::kWidgetRoundedCorner));

  paintChildrenBackgrounds(g);
  paintBorder(g);
}

void SampleSection::setActive(bool active) {
  sample_viewer_->setActive(active);
  SynthSection::setActive(active);
}

void SampleSection::resized() {
  SynthSection::resized();

  preset_selector_->setColour(Skin::kIconButtonOff, findColour(Skin::kUiButton, true));
  preset_selector_->setColour(Skin::kIconButtonOffHover, findColour(Skin::kUiButtonHover, true));
  preset_selector_->setColour(Skin::kIconButtonOffPressed, findColour(Skin::kUiButtonPressed, true));

  destination_text_->setColor(findColour(Skin::kBodyText, true));

  // Column layout to match the oscillators either side of it: name, tuning,
  // the waveform itself, its toggles, then level and pan.
  int title_width = getTitleWidth();
  int widget_margin = findValue(Skin::kWidgetMargin);
  int label_height = findValue(Skin::kLabelBackgroundHeight);
  int text_height = findValue(Skin::kTextButtonHeight);
  int knob_section_height = getKnobSectionHeight();
  int w = getWidth();
  int h = getHeight();
  int inner_width = w - 2 * widget_margin;

  int header_height = title_width - 2 * widget_margin;
  int joint_height = text_height + widget_margin;
  int toggles_height = text_height + widget_margin;

  int y = widget_margin;
  preset_selector_->setBounds(widget_margin, y, inner_width, header_height);
  y += header_height + widget_margin;

  placeJointControls(widget_margin, y, inner_width, joint_height,
                     transpose_.get(), tune_.get(), transpose_quantize_button_.get());
  y += joint_height + widget_margin;

  int bottom_stack = toggles_height + widget_margin + knob_section_height + label_height + widget_margin;
  int viewer_height = std::max(h - y - bottom_stack - widget_margin, text_height);
  sample_viewer_->setBounds(widget_margin, y, inner_width, viewer_height);
  y += viewer_height + widget_margin;

  Button* toggles[] = { keytrack_.get(), loop_.get(), random_phase_.get(), bounce_.get() };
  int num_toggles = 4;
  int toggle_width = (inner_width - (num_toggles - 1) * widget_margin) / num_toggles;
  int toggle_size = std::min(toggles_height, toggle_width);
  for (int i = 0; i < num_toggles; ++i) {
    toggles[i]->setBounds(widget_margin + i * (toggle_width + widget_margin), y, toggle_size, toggle_size);
  }
  y += toggles_height + widget_margin;

  placeKnobsInArea(Rectangle<int>(0, y, w, knob_section_height), { level_.get(), pan_.get() });

  int destination_y = h - label_height - widget_margin;
  destination_selector_->setBounds(widget_margin, destination_y, inner_width, label_height);
  destination_text_->setBounds(destination_selector_->getBounds());
  destination_text_->setTextSize(findValue(Skin::kLabelHeight));
  prev_destination_->setBounds(widget_margin, destination_y, label_height, label_height);
  next_destination_->setBounds(destination_selector_->getRight() - label_height, destination_y,
                               label_height, label_height);
}

void SampleSection::reset() {
  SynthSection::reset();
  preset_selector_->setText(sample_viewer_->getName());
  sample_viewer_->repaintAudio();
}

void SampleSection::loadFile(const File& file) {
  static constexpr int kMaxFileSamples = 17640000;
  preset_selector_->setText(file.getFileNameWithoutExtension());
  sample_->setLastBrowsedFile(file.getFullPathName().toStdString());

  std::unique_ptr<AudioFormatReader> format_reader(sample_viewer_->formatManager().createReaderFor(file));

  if (format_reader) {
    int num_samples = (int)std::min<long long>(format_reader->lengthInSamples, kMaxFileSamples);
    sample_buffer_.setSize(format_reader->numChannels, num_samples);
    format_reader->read(&sample_buffer_, 0, num_samples, 0, true, true);
    if (sample_buffer_.getNumChannels() > 1) {
      sample_->loadSample(sample_buffer_.getReadPointer(0), sample_buffer_.getReadPointer(1),
                          num_samples, format_reader->sampleRate);
    }
    else
      sample_->loadSample(sample_buffer_.getReadPointer(0), num_samples, format_reader->sampleRate);
    sample_->setName(file.getFileNameWithoutExtension().toStdString());
  }

  preset_selector_->setText(sample_viewer_->getName());
  sample_viewer_->repaintAudio();
}

void SampleSection::setAllValues(vital::control_map& controls) {
  preset_selector_->setText(sample_viewer_->getName());
  transpose_quantize_button_->setValue(static_cast<int>(controls["sample_transpose_quantize"]->value()));
  SynthSection::setAllValues(controls);

  current_destination_ = controls[destination_control_name_]->value();
  setupDestination();
}

void SampleSection::buttonClicked(Button* clicked_button) {
  if (clicked_button == destination_selector_.get()) {
    PopupItems options;
    int num_source_destinations = vital::constants::kNumSourceDestinations;
    for (int i = 0; i < num_source_destinations; ++i)
      options.addItem(i, strings::kDestinationMenuNames[i]);

    showPopupSelector(this, Point<int>(clicked_button->getX(), clicked_button->getBottom()),options,
                      [=](int selection) { setDestinationSelected(selection); });
  }
  else if (clicked_button == prev_destination_.get()) {
    int new_destination = current_destination_ - 1 + vital::constants::kNumSourceDestinations;
    setDestinationSelected(new_destination % vital::constants::kNumSourceDestinations);
  }
  else if (clicked_button == next_destination_.get()) {
    int new_destination = (current_destination_ + 1) % vital::constants::kNumSourceDestinations;
    setDestinationSelected(new_destination);
  }
  else
    SynthSection::buttonClicked(clicked_button);
}

void SampleSection::setDestinationSelected(int selection) {
  current_destination_ = selection;
  setupDestination();

  SynthGuiInterface* parent = findParentComponentOfClass<SynthGuiInterface>();
  if (parent)
    parent->getSynth()->valueChangedInternal(destination_control_name_, current_destination_);
}

void SampleSection::setupDestination() {
  for (Listener* listener : listeners_)
    listener->sampleDestinationChanged(this, current_destination_);

  destination_text_->setText(strings::kDestinationNames[current_destination_]);
}

void SampleSection::toggleFilterInput(int filter_index, bool on) {
  vital::constants::SourceDestination current_destination = (vital::constants::SourceDestination)current_destination_;
  if (filter_index == 0)
    setDestinationSelected(vital::constants::toggleFilter1(current_destination, on));
  else
    setDestinationSelected(vital::constants::toggleFilter2(current_destination, on));
}

void SampleSection::prevClicked() {
  File sample_file = LoadSave::getShiftedFile(LoadSave::kSampleFolderName, vital::kSampleExtensionsList,
                                              LoadSave::kAdditionalSampleFoldersName, getCurrentFile(), -1);
  if (sample_file.exists())
    loadFile(sample_file);
  
  updatePopupBrowser(this);
}

void SampleSection::nextClicked() {
  File sample_file = LoadSave::getShiftedFile(LoadSave::kSampleFolderName, vital::kSampleExtensionsList,
                                              LoadSave::kAdditionalSampleFoldersName, getCurrentFile(), 1);
  if (sample_file.exists())
    loadFile(sample_file);
  
  updatePopupBrowser(this);
}

void SampleSection::textMouseDown(const MouseEvent& e) {
  static constexpr int kBrowserWidth = 450;
  static constexpr int kBrowserHeight = 300;

  Rectangle<int> bounds(preset_selector_->getRight(), preset_selector_->getY(),
                        kBrowserWidth * size_ratio_, kBrowserHeight * size_ratio_);
  bounds = getLocalArea(this, bounds);
  showPopupBrowser(this, bounds, LoadSave::getSampleDirectories(), vital::kSampleExtensionsList,
                   LoadSave::kSampleFolderName, LoadSave::kAdditionalSampleFoldersName);
}

void SampleSection::quantizeUpdated() {
  int value = transpose_quantize_button_->getValue();
  SynthGuiInterface* parent = findParentComponentOfClass<SynthGuiInterface>();
  if (parent)
    parent->getSynth()->valueChangedInternal("sample_transpose_quantize", value);
}
