package com.securemed.app.ui.components

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavController
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.currentBackStackEntryAsState
import com.securemed.app.navigation.Route

data class BottomNavItem(
    val route: String,
    val title: String,
    val icon: ImageVector
)

@Composable
fun BottomNavBar(navController: NavController) {
    val items = listOf(
        BottomNavItem(Route.Dashboard.route, "الرئيسية", Icons.Default.Home),
        BottomNavItem(Route.Patients.route, "المرضى", Icons.Default.People),
        BottomNavItem(Route.Channels.route, "المحادثات", Icons.Default.Chat),
        BottomNavItem(Route.Profile.route, "حسابي", Icons.Default.Person)
    )

    val navBackStackEntry = navController.currentBackStackEntryAsState().value
    val currentRoute = navBackStackEntry?.destination?.route

    if (items.any { it.route == currentRoute }) {
        NavigationBar {
            items.forEach { item ->
                NavigationBarItem(
                    icon = { Icon(item.icon, contentDescription = item.title) },
                    label = { Text(item.title) },
                    selected = currentRoute == item.route,
                    onClick = {
                        navController.navigate(item.route) {
                            popUpTo(navController.graph.findStartDestination().id) {
                                saveState = true
                            }
                            launchSingleTop = true
                            restoreState = true
                        }
                    }
                )
            }
        }
    }
}
