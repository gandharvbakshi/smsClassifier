package com.smsclassifier.app.ui.components

import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.smsclassifier.app.ui.viewmodel.FilterType

@OptIn(ExperimentalMaterial3Api::class)
@Composable
@Suppress("UNUSED_PARAMETER")
fun FilterChips(
    selectedFilter: FilterType,
    onFilterSelected: (FilterType) -> Unit,
    counts: Map<FilterType, Int>,
    modifier: Modifier = Modifier,
    filterOrder: List<FilterType> = FilterType.values().toList()
) {
    var overflowExpanded by remember { mutableStateOf(false) }
    val primaryFilters = listOf(FilterType.OTP, FilterType.PHISHING, FilterType.ALL)

    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        SingleChoiceSegmentedButtonRow(modifier = Modifier.weight(1f)) {
            primaryFilters.forEachIndexed { index, filter ->
                SegmentedButton(
                    selected = selectedFilter == filter,
                    onClick = { onFilterSelected(filter) },
                    shape = SegmentedButtonDefaults.itemShape(index = index, count = primaryFilters.size)
                ) {
                    Text("${filterLabel(filter)} (${counts[filter] ?: 0})")
                }
            }
        }
        Box {
            IconButton(onClick = { overflowExpanded = true }) {
                Icon(Icons.Default.MoreVert, contentDescription = "More filters")
            }
            DropdownMenu(
                expanded = overflowExpanded,
                onDismissRequest = { overflowExpanded = false }
            ) {
                DropdownMenuItem(
                    text = { Text("Needs review (${counts[FilterType.NEEDS_REVIEW] ?: 0})") },
                    onClick = {
                        onFilterSelected(FilterType.NEEDS_REVIEW)
                        overflowExpanded = false
                    }
                )
                DropdownMenuItem(
                    text = { Text("Personal (${counts[FilterType.GENERAL] ?: 0})") },
                    onClick = {
                        onFilterSelected(FilterType.GENERAL)
                        overflowExpanded = false
                    }
                )
            }
        }
    }
}

private fun filterLabel(filter: FilterType): String = when (filter) {
    FilterType.OTP -> "OTP"
    FilterType.PHISHING -> "Phishing"
    FilterType.NEEDS_REVIEW -> "Needs review"
    FilterType.GENERAL -> "Personal"
    FilterType.ALL -> "All"
}
