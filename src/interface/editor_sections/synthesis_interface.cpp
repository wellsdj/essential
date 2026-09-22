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

#include "synthesis_interface.h"

#include "filter_section.h"
#include "oscillator_section.h"
#include "producers_module.h"
#include "synth_oscillator.h"
#include "sample_section.h"

SynthesisInterface::SynthesisInterface(Authentication* auth,
                                       const vital::output_map& mono_modulations,
                                       const vital::output_map& poly_modulations) : SynthSection("synthesis") {
  filter_section_2_ = std::make_unique<FilterSection>(2, mono_modulations, poly_modulations);
  addSubSection(filter_section_2_.get());
  filter_section_2_->addListener(this);

  filter_section_1_ = std::make_unique<FilterSection>(1, mono_modulations, poly_modulations);
  addSubSection(filter_section_1_.get());
  filter_section_1_->addListener(this);

  for (int i = 0; i < vital::kNumOscillators; ++i) {
    oscillators_[i] = std::make_unique<OscillatorSection>(auth, i, mono_modulations, poly_modulations);
    addSubSection(oscillators_[i].get());
    oscillators_[i]->addListener(this);
  }

  sample_section_ = std::make_unique<SampleSection>("SMP");
  addSubSection(sample_section_.get());
  sample_section_->addListener(this);

  setOpaque(false);
}

SynthesisInterface::~SynthesisInterface() { }

void SynthesisInterface::paintBackground(Graphics& g) {
  paintChildrenBackgrounds(g);
}

void SynthesisInterface::resized() {
  // Serum-style strip: the oscillators, the sample/noise source and both
  // filters sit side by side across the top rather than stacked, so every
  // sound source is visible at once.
  int padding = getPadding();
  int num_columns = vital::kNumOscillators + 3;   // oscillators + sample + 2 filters
  int total_padding = padding * (num_columns - 1);
  int usable = getWidth() - total_padding;

  // oscillators carry a wavetable display, so they get more width than the
  // sample source and the filters
  float osc_weight = 1.25f;
  float other_weight = 1.0f;
  float total_weight = vital::kNumOscillators * osc_weight + 3 * other_weight;
  int osc_width = usable * osc_weight / total_weight;
  int other_width = usable * other_weight / total_weight;

  int x = 0;
  for (int i = 0; i < vital::kNumOscillators; ++i) {
    oscillators_[i]->setBounds(x, 0, osc_width, getHeight());
    x += osc_width + padding;
  }

  sample_section_->setBounds(x, 0, other_width, getHeight());
  x += other_width + padding;

  filter_section_1_->setBounds(x, 0, other_width, getHeight());
  x += other_width + padding;

  // the last column takes whatever rounding left over
  filter_section_2_->setBounds(x, 0, getWidth() - x, getHeight());

  SynthSection::resized();
}

void SynthesisInterface::visibilityChanged() {
  if (isShowing()) {
    for (int i = 0; i < vital::kNumOscillators; ++i)
      oscillators_[i]->loadBrowserState();
  }
}

void SynthesisInterface::distortionTypeChanged(OscillatorSection* section, int distortion_type) {
  bool dependents[vital::kNumOscillators];
  for (int i = 0; i < vital::kNumOscillators; ++i)
    dependents[i] = false;

  int index = section->index();
  int last_index = index;
  while (!dependents[index]) {
    dependents[index] = true;
    last_index = index;
    int type = oscillators_[index]->getDistortion();
    if (vital::SynthOscillator::isFirstModulation(type))
      index = vital::ProducersModule::getFirstModulationIndex(index);
    else if (vital::SynthOscillator::isSecondModulation(type))
      index = vital::ProducersModule::getSecondModulationIndex(index);
    else
      return;
  }

  oscillators_[last_index]->resetOscillatorModulationDistortionType();
}

void SynthesisInterface::oscillatorDestinationChanged(OscillatorSection* section, int destination) {
  bool filter1_on = destination == vital::constants::kFilter1 || destination == vital::constants::kDualFilters;
  bool filter2_on = destination == vital::constants::kFilter2 || destination == vital::constants::kDualFilters;
  for (int i = 0; i < vital::kNumOscillators; ++i) {
    if (oscillators_[i].get() == section) {
      filter_section_1_->setOscillatorInput(i, filter1_on);
      filter_section_2_->setOscillatorInput(i, filter2_on);
    }
  }
}

void SynthesisInterface::filterSerialSelected(FilterSection* section) {
  if (section == filter_section_1_.get())
    filter_section_2_->clearFilterInput();
  else
    filter_section_1_->clearFilterInput();
}

void SynthesisInterface::oscInputToggled(FilterSection* section, int index, bool on) {
  int filter_index = section == filter_section_1_.get() ? 0 : 1;
  oscillators_[index]->toggleFilterInput(filter_index, on);
}

void SynthesisInterface::sampleInputToggled(FilterSection* section, bool on) {
  int filter_index = section == filter_section_1_.get() ? 0 : 1;
  sample_section_->toggleFilterInput(filter_index, on);
}

void SynthesisInterface::sampleDestinationChanged(SampleSection* section, int destination) {
  bool filter1_on = destination == vital::constants::kFilter1 || destination == vital::constants::kDualFilters;
  bool filter2_on = destination == vital::constants::kFilter2 || destination == vital::constants::kDualFilters;
  filter_section_1_->setSampleInput(filter1_on);
  filter_section_2_->setSampleInput(filter2_on);
}

