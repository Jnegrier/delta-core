/*
 * Copyright 2019 EPAM Systems
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.epam.reportportal.aspect;

import com.epam.reportportal.annotations.Step;
import com.epam.reportportal.annotations.StepTemplateConfig;
import com.epam.reportportal.utils.StepTemplateUtils;
import com.google.common.collect.ImmutableMap;
import io.reactivex.annotations.Nullable;
import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.reflect.MethodSignature;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * @author <a href="mailto:ivan_budayeu@epam.com">Ivan Budayeu</a>
 */
class StepNameUtils {

	private static final Logger LOGGER = LoggerFactory.getLogger(StepNameUtils.class);

	private static final String STEP_GROUP = "\\{([\\w$]+(\\.[\\w$]+)*)}";

	private StepNameUtils() {
		//static only
	}

	static String getStepName(Step step, MethodSignature signature, JoinPoint joinPoint) {
		String nameTemplate = step.value();
		if (nameTemplate.trim().isEmpty()) {
			return signature.getMethod().getName();
		}
		Matcher matcher = Pattern.compile(STEP_GROUP).matcher(nameTemplate);
		Map<String, Object> parametersMap = createParamsMapping(step.templateConfig(), signature, joinPoint.getArgs());

		StringBuffer stringBuffer = new StringBuffer();
		while (matcher.find()) {
			String templatePart = matcher.group(1);
			String replacement = getReplacement(templatePart, parametersMap, step.templateConfig());
			matcher.appendReplacement(stringBuffer, replacement != null ? replacement : matcher.group(0));
		}
		matcher.appendTail(stringBuffer);
		return stringBuffer.toString();
	}

	private static Map<String, Object> createParamsMapping(StepTemplateConfig templateConfig, MethodSignature signature,
			final Object... args) {
		int paramsCount = Math.max(signature.getParameterNames().length, args.length);
		ImmutableMap.Builder<String, Object> builder = ImmutableMap.builder();
		builder.put(templateConfig.methodNameTemplate(), signature.getMethod().getName());
		for (int i = 0; i < paramsCount; i++) {
			builder.put(signature.getParameterNames()[i], args[i]);
			builder.put(Integer.toString(i), args[i]);
		}
		return builder.build();
	}

	@Nullable
	private static String getReplacement(String templatePart, Map<String, Object> parametersMap, StepTemplateConfig templateConfig) {
		String[] fields = templatePart.split("\\.");
		String variableName = fields[0];
		Object param = parametersMap.get(variableName);
		if (param == null) {
			LOGGER.error("Param - " + variableName + " was not found");
			return null;
		}
		try {
			return StepTemplateUtils.retrieveValue(templateConfig, 1, fields, param);
		} catch (NoSuchFieldException e) {
			LOGGER.error("Unable to parse: " + templatePart);
			return null;
		}
	}
}
