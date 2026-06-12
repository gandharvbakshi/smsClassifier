package com.smsclassifier.app.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.AppContainer
import com.smsclassifier.app.ui.viewmodel.FilterType

/**
 * Horizontally scrollable filter pills.
 * - Always shows "All".
 * - Other filters appear only when their count > 0 (no empty-state clutter).
 * - Counts shown as " · 163" suffix (or omitted if 0 / null).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FilterChips(
    selectedFilter: FilterType,
    onFilterSelected: (FilterType) -> Unit,
    counts: Map<FilterType, Int>,
    modifier: Modifier = Modifier,
    @Suppress("UNUSED_PARAMETER") filterOrder: List<FilterType> = FilterType.entries.toList()
) {
    val orderedFilters = buildList {
        add(FilterType.ALL)
        listOf(
            FilterType.OTP,
            FilterType.PHISHING,
            FilterType.NEEDS_REVIEW,
            FilterType.GENERAL
        ).forEach { f ->
            if ((counts[f] ?: 0) > 0) add(f)
        }
    }

    LazyRow(
        modifier = modifier.fillMaxWidth(),
        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        items(orderedFilters) { filter ->
            val count = counts[filter] ?: 0
            val label = filterLabel(filter) +
                if (count > 0) "  ·  $count" else ""

            FilterChip(
                selected = selectedFilter == filter,
                onClick = {
                    AppContainer.telemetry.logFilterChanged(filter.name)
                    onFilterSelected(filter)
                },
                label = {
                    Text(
                        text = label,
                        style = MaterialTheme.typography.labelLarge
                    )
                },
                shape = RoundedCornerShape(50),
                colors = FilterChipDefaults.filterChipColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    labelColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                    selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer
                ),
                border = FilterChipDefaults.filterChipBorder(
                    enabled = true,
                    selected = selectedFilter == filter,
                    borderColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.4f),
                    selectedBorderColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.0f),
                    borderWidth = 1.dp
                )
            )
        }
    }
}

private fun filterLabel(filter: FilterType): String = when (filter) {
    FilterType.OTP -> "OTP"
    FilterType.PHISHING -> "Scam"
    FilterType.NEEDS_REVIEW -> "Review"
    FilterType.GENERAL -> "Personal"
    FilterType.ALL -> "All"
}
