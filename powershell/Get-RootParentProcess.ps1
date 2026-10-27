#Requires -Version 7.0

<#
.SYNOPSIS
    Finds the root parent process(es) for a given process name or process ID and
    shows the process tree(s) beneath them.

.DESCRIPTION
    This cmdlet traverses the process hierarchy to identify the topmost parent process(es)
    that share the same process name (the "roots"). When querying by process name, it can
    identify multiple roots if there are multiple independent process trees. When querying
    by process ID, it returns only the tree containing that specific process.

    By default, each root is returned along with all of its same-name descendants, ordered
    so that every child appears directly below its parent. Use -RootOnly to return only the
    roots.

    Returns System.Diagnostics.Process objects, just like Get-Process, allowing familiar
    pipeline manipulation. Each object is decorated with these extra properties:

        ParentId       ID of the parent process (or $null if there is none)
        ParentName     Name of the parent process (or $null if there is none)
        ParentProcess  The parent's full System.Diagnostics.Process object (or $null)
        Depth          0 for a root, 1 for its children, and so on
        RootId         ID of the root of the tree this process belongs to

    The parent of a root (e.g. explorer for Dropbox) is never returned as its own object,
    so piping to Stop-Process cannot touch it. It is shown in the root's ParentId and
    ParentName columns and is available through the root's ParentProcess property.

.PARAMETER ProcessName
    The name of the process to analyze (e.g., 'msedge', 'chrome'). This parameter is
    mutually exclusive with ProcessId. May return multiple process trees.

.PARAMETER ProcessId
    The ID of a specific process to analyze. This parameter is mutually exclusive
    with ProcessName. Returns the single tree containing that process.

.PARAMETER RootOnly
    Return only the root process(es), without their descendants.

.PARAMETER AsTree
    Return the hierarchy as lines of text drawn with ASCII connectors instead of
    Process objects. Roots that share a parent are grouped under a single line for
    that parent.

.EXAMPLE
    Get-RootParentProcess -ProcessName dropbox

    ParentId ParentName    Id Name
    -------- ----------    -- ----
       16708 explorer   22468 Dropbox
       22468 Dropbox    20440 Dropbox
       22468 Dropbox    38448 Dropbox
       16708 explorer   37512 Dropbox
       37512 Dropbox    38504 Dropbox

    Returns every Dropbox process tree, with each child listed below its parent.

.EXAMPLE
    Get-RootParentProcess -ProcessName dropbox -AsTree

    16708 explorer
    |-- 22468 Dropbox
    |   |-- 20440 Dropbox
    |   `-- 38448 Dropbox
    `-- 37512 Dropbox
        `-- 38504 Dropbox

    Shows the same trees as text.

.EXAMPLE
    Get-RootParentProcess -ProcessName msedge -RootOnly

    Returns only the root msedge process(es). If there are multiple independent process
    trees (e.g., 10->11->12 and 20->21->22), it returns both roots (e.g., 10 and 20).

.EXAMPLE
    Get-RootParentProcess -ProcessName msedge | Select-Object Id, ProcessName, StartTime, Depth

    Selects properties just like Get-Process. All Process members remain available;
    run the output through Get-Member to see them.

.EXAMPLE
    (Get-RootParentProcess -ProcessName dropbox -RootOnly).ParentProcess

    Gets the full Process object for the parent of each root (e.g. explorer).

.EXAMPLE
    Get-RootParentProcess -ProcessId 12345

    Returns the tree containing the process with ID 12345, starting from its root.

.EXAMPLE
    Get-RootParentProcess -ProcessName chrome -RootOnly | Stop-Process -WhatIf

    Shows what would happen if you stopped all root Chrome processes.

.OUTPUTS
    System.Diagnostics.Process, or System.String when -AsTree is used.

.NOTES
    Author: Chris Leonard
    Version: 3.0
    Requires PowerShell 7 or later (uses the Process.Parent property).
#>

# Register the default table view (ParentId, ParentName, Id, Name) for decorated objects.
if (-not (Get-FormatData -TypeName 'RootParentProcess.Node' -ErrorAction SilentlyContinue)) {
    $formatPath = Join-Path ([System.IO.Path]::GetTempPath()) 'RootParentProcess.format.ps1xml'
    @'
<?xml version="1.0" encoding="utf-8"?>
<Configuration>
  <ViewDefinitions>
    <View>
      <Name>RootParentProcess.Node</Name>
      <ViewSelectedBy>
        <TypeName>RootParentProcess.Node</TypeName>
      </ViewSelectedBy>
      <TableControl>
        <AutoSize />
        <TableHeaders>
          <TableColumnHeader><Label>ParentId</Label><Alignment>Right</Alignment></TableColumnHeader>
          <TableColumnHeader><Label>ParentName</Label></TableColumnHeader>
          <TableColumnHeader><Label>Id</Label><Alignment>Right</Alignment></TableColumnHeader>
          <TableColumnHeader><Label>Name</Label></TableColumnHeader>
        </TableHeaders>
        <TableRowEntries>
          <TableRowEntry>
            <TableColumnItems>
              <TableColumnItem><PropertyName>ParentId</PropertyName></TableColumnItem>
              <TableColumnItem><PropertyName>ParentName</PropertyName></TableColumnItem>
              <TableColumnItem><PropertyName>Id</PropertyName></TableColumnItem>
              <TableColumnItem><PropertyName>ProcessName</PropertyName></TableColumnItem>
            </TableColumnItems>
          </TableRowEntry>
        </TableRowEntries>
      </TableControl>
    </View>
  </ViewDefinitions>
</Configuration>
'@ | Set-Content -Path $formatPath -Encoding utf8
    Update-FormatData -PrependPath $formatPath
}

function Get-RootParentProcess {
    [CmdletBinding(DefaultParameterSetName='ByName')]
    [OutputType([System.Diagnostics.Process], [string])]
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
        [int]$ProcessId,

        [switch]$RootOnly,

        [switch]$AsTree
    )

    begin {
        Write-Verbose "Starting Get-RootParentProcess cmdlet"

        # Emits one line per node, then recurses into its children.
        function Format-TreeBranch {
            param($Node, [string]$Prefix, [bool]$IsLast, $ChildMap, $Visited)

            $connector = if ($IsLast) { '`-- ' } else { '|-- ' }
            "$Prefix$connector$($Node.Id) $($Node.ProcessName)"

            if (-not $Visited.Add($Node.Id)) { return }
            $children = @(if ($ChildMap.ContainsKey($Node.Id)) { $ChildMap[$Node.Id] })
            $childPrefix = $Prefix + $(if ($IsLast) { '    ' } else { '|   ' })
            for ($i = 0; $i -lt $children.Count; $i++) {
                Format-TreeBranch -Node $children[$i] -Prefix $childPrefix `
                    -IsLast ($i -eq $children.Count - 1) -ChildMap $ChildMap -Visited $Visited
            }
        }
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
                $target = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
                if ($target) { Get-Process -Name $target.ProcessName -ErrorAction SilentlyContinue }
            }
        }

        if (-not $processes) {
            Write-Warning "No processes found matching the specified criteria."
            return
        }

        $processArray = @($processes)
        Write-Verbose "Found $($processArray.Count) process(es) named $($processArray[0].ProcessName)"

        # Look up each parent once; .Parent is $null if the parent has exited.
        $byId = @{}
        $parentOf = @{}
        foreach ($proc in $processArray) {
            $byId[$proc.Id] = $proc
            $parentOf[$proc.Id] = $proc.Parent
        }

        # Build the child lists (same-name children only) and find the roots: processes
        # whose parent is missing or has a different name.
        $childMap = @{}
        $roots = [System.Collections.Generic.List[object]]::new()
        foreach ($proc in ($processArray | Sort-Object Id)) {
            $parent = $parentOf[$proc.Id]
            if ($parent -and $byId.ContainsKey($parent.Id) -and $parent.Id -ne $proc.Id) {
                if (-not $childMap.ContainsKey($parent.Id)) {
                    $childMap[$parent.Id] = [System.Collections.Generic.List[object]]::new()
                }
                $childMap[$parent.Id].Add($proc)
            }
            else {
                Write-Verbose "  Root: $($proc.Id); Parent: $(if ($parent) { "$($parent.Id) $($parent.ProcessName)" } else { 'none' })"
                $roots.Add($proc)
            }
        }

        # When querying by ID, keep only the root of the target's tree.
        if ($PSCmdlet.ParameterSetName -eq 'ById') {
            $currentId = $ProcessId
            $visitedIds = [System.Collections.Generic.HashSet[int]]::new()
            while ($visitedIds.Add($currentId)) {
                $parent = $parentOf[$currentId]
                if (-not $parent -or -not $byId.ContainsKey($parent.Id)) { break }
                $currentId = $parent.Id
            }
            Write-Verbose "Root for process ID $ProcessId is $currentId"
            $roots = @($roots | Where-Object Id -eq $currentId)
        }

        if ($roots.Count -eq 0) {
            Write-Warning "No root process found (possible circular parent references)."
            return
        }

        $roots = @($roots | Sort-Object @{ Expression = { $p = $parentOf[$_.Id]; if ($p) { $p.Id } else { -1 } } }, Id)
        Write-Verbose "Found $($roots.Count) root parent(s): $($roots.Id -join ', ')"

        if ($RootOnly) { $childMap = @{} }

        if ($AsTree) {
            $visited = [System.Collections.Generic.HashSet[int]]::new()
            $i = 0
            while ($i -lt $roots.Count) {
                $parent = $parentOf[$roots[$i].Id]
                if (-not $parent) {
                    # No parent: the root itself starts at the left margin.
                    $root = $roots[$i]
                    "$($root.Id) $($root.ProcessName)"
                    [void]$visited.Add($root.Id)
                    $children = @(if ($childMap.ContainsKey($root.Id)) { $childMap[$root.Id] })
                    for ($c = 0; $c -lt $children.Count; $c++) {
                        Format-TreeBranch -Node $children[$c] -Prefix '' `
                            -IsLast ($c -eq $children.Count - 1) -ChildMap $childMap -Visited $visited
                    }
                    $i++
                    continue
                }

                # Group consecutive roots that share this parent under one heading.
                $group = [System.Collections.Generic.List[object]]::new()
                while ($i -lt $roots.Count -and $parentOf[$roots[$i].Id] -and $parentOf[$roots[$i].Id].Id -eq $parent.Id) {
                    $group.Add($roots[$i])
                    $i++
                }
                "$($parent.Id) $($parent.ProcessName)"
                for ($g = 0; $g -lt $group.Count; $g++) {
                    Format-TreeBranch -Node $group[$g] -Prefix '' `
                        -IsLast ($g -eq $group.Count - 1) -ChildMap $childMap -Visited $visited
                }
            }
            return
        }

        # Walk each tree depth-first so every child is emitted right after its parent.
        $visited = [System.Collections.Generic.HashSet[int]]::new()
        foreach ($root in $roots) {
            $stack = [System.Collections.Generic.Stack[object]]::new()
            $stack.Push(@($root, 0))
            while ($stack.Count -gt 0) {
                $proc, $depth = $stack.Pop()
                if (-not $visited.Add($proc.Id)) { continue }

                $parent = $parentOf[$proc.Id]
                $proc | Add-Member -NotePropertyMembers ([ordered]@{
                    ParentId      = if ($parent) { $parent.Id } else { $null }
                    ParentName    = if ($parent) { $parent.ProcessName } else { $null }
                    ParentProcess = $parent
                    Depth         = $depth
                    RootId        = $root.Id
                }) -Force
                if ($proc.PSObject.TypeNames[0] -ne 'RootParentProcess.Node') {
                    $proc.PSObject.TypeNames.Insert(0, 'RootParentProcess.Node')
                }
                Write-Output $proc

                # Push children in reverse so they pop in ascending ID order.
                $children = @(if ($childMap.ContainsKey($proc.Id)) { $childMap[$proc.Id] })
                for ($c = $children.Count - 1; $c -ge 0; $c--) {
                    $stack.Push(@($children[$c], ($depth + 1)))
                }
            }
        }
    }

    end {
        Write-Verbose "Get-RootParentProcess cmdlet completed"
    }
}
