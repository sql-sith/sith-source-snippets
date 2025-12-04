<#
.SYNOPSIS
    Finds the root parent process(es) for a given process name or process ID.

.DESCRIPTION
    This cmdlet traverses the process hierarchy to identify the topmost parent process(es)
    that share the same process name. When querying by process name, it can identify
    multiple root parents if there are multiple independent process trees. When querying
    by process ID, it returns the single root parent for that specific process.
    
    Returns System.Diagnostics.Process objects, just like Get-Process, allowing familiar
    pipeline manipulation.

.PARAMETER ProcessName
    The name of the process to analyze (e.g., 'msedge', 'chrome'). This parameter is
    mutually exclusive with ProcessId. May return multiple root parent processes if multiple
    process trees exist.

.PARAMETER ProcessId
    The ID of a specific process to analyze. This parameter is mutually exclusive
    with ProcessName. Returns a single root parent process.

.EXAMPLE
    Get-RootParentProcess -ProcessName msedge
    
    Finds all root parent processes for processes named 'msedge'. If there are
    multiple independent process trees (e.g., 10->11->12 and 20->21->22), it will
    return both root process roots (e.g., @(10, 20).

.EXAMPLE
    Get-RootParentProcess -ProcessName msedge | Select-Object Id, ProcessName, StartTime
    
    Gets root parent processes and displays specific properties, just like Get-Process.

.EXAMPLE
    Get-RootParentProcess -ProcessId 12345
    
    Finds the root parent process for the process with ID 12345 by traversing
    up the process tree until the topmost parent with the same name is found.

.EXAMPLE
    Get-RootParentProcess -ProcessName chrome | Stop-Process -WhatIf
    
    Shows what would happen if you stopped all root parent Chrome processes.

.OUTPUTS
    System.Diagnostics.Process or System.Diagnostics.Process[]
    Returns the root parent process(es). May return an array when using ProcessName 
    parameter with multiple process trees.

.NOTES
    Author: Chris Leonard
    Version: 2.1
#>

function Get-RootParentProcess {
    [CmdletBinding(DefaultParameterSetName='ByName')]
    param(
        [Parameter(
            Mandatory=$true,
            ParameterSetName='ByName',
            Position=0,
            ValueFromPipeline=$true,
            ValueFromPipelineByPropertyName=$true,
            HelpMessage="Enter the process name (e.g., msedge, chrome)"
        )]
        [ValidateNotNullOrEmpty()]
        [string]$ProcessName,

        [Parameter(
            Mandatory=$true,
            ParameterSetName='ById',
            Position=0,
            ValueFromPipeline=$true,
            ValueFromPipelineByPropertyName=$true,
            HelpMessage="Enter the process ID"
        )]
        [ValidateRange(1, [int]::MaxValue)]
        [int]$ProcessId
    )

    begin {
        Write-Verbose "Starting Get-RootParentProcess cmdlet"
    }

    process {
        # Get the process(es) based on parameter set
        $processes = switch ($PSCmdlet.ParameterSetName) {
            'ByName' {
                Write-Verbose "Retrieving processes by name: $ProcessName"
                Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
            }
            'ById' {
                Write-Verbose "Retrieving process by ID: $ProcessId"
                Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
            }
        }

        if (-not $processes) {
            Write-Warning "No processes found matching the specified criteria."
            return
        }

        # Convert to array and get the process name we're looking for
        $processArray = @($processes)
        $targetProcessName = $processArray[0].ProcessName
        
        # Different verbose message based on parameter set
        if ($PSCmdlet.ParameterSetName -eq 'ById') {
            Write-Verbose "Finding root parent for process ID: $ProcessId"
        }
        else {
            Write-Verbose "Finding root parent(s) for process name: $targetProcessName"
        }
        
        # For each process, find its root parent by traversing up the tree
        $rootParentIds = @()
        
        foreach ($proc in $processArray) {
            Write-Verbose "Examining process ID: $($proc.Id)"
            
            # Traverse up to find the root for this specific process
            $currentProcess = $proc
            $root_parent_id = $currentProcess.Id
            $visitedIds = @($currentProcess.Id)
            
            while ($true) {
                try {
                    $parent = Get-Process -Id $currentProcess.Parent.Id -ErrorAction SilentlyContinue
                    $parent_id = if ($parent) { $parent.Id } else { 0 }
                    
                    Write-Verbose "  Current: $($currentProcess.Id); Parent ID: $parent_id; Root: $root_parent_id"
                    
                    if (-not $parent_id -or $parent_id -eq 0) {
                        Write-Verbose "  No more parents. Root is: $root_parent_id"
                        break
                    }
                    
                    if ($parent_id -in $visitedIds) {
                        Write-Verbose "  Circular reference detected. Root is: $root_parent_id"
                        break
                    }
                    
                    # Check if parent has the same process name
                    if ($parent.ProcessName -eq $targetProcessName) {
                        $root_parent_id = $parent_id
                        $visitedIds += $parent_id
                        $currentProcess = $parent
                        Write-Verbose "  Parent has same name. Updated root to: $root_parent_id"
                    }
                    else {
                        Write-Verbose "  Parent has different name ($($parent.ProcessName)). Root is: $root_parent_id"
                        break
                    }
                }
                catch {
                    Write-Verbose "  Error accessing parent: $_"
                    break
                }
            }
            
            # Add this root if not already found
            if ($root_parent_id -notin $rootParentIds) {
                $rootParentIds += $root_parent_id
                Write-Verbose "Added new root parent: $root_parent_id"
            }
        }
        
        Write-Verbose "Found $($rootParentIds.Count) root parent(s): $($rootParentIds -join ', ')"
        
        # Get and return the actual process objects
        foreach ($rootId in $rootParentIds) {
            try {
                $rootProcess = Get-Process -Id $rootId -ErrorAction Stop
                Write-Output $rootProcess
            }
            catch {
                Write-Warning "Could not retrieve process object for ID $rootId : $_"
            }
        }
    }

    end {
        Write-Verbose "Get-RootParentProcess cmdlet completed"
    }
}